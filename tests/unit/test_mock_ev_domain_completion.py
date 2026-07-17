"""Regression tests for the mock Enterprise Vault domain completion scenario."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from adapters.source import MockEnterpriseVaultSourceAdapter
from domain.enums.archive_type import ArchiveType
from domain.enums.item_type import ItemType
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from migration_engine.discovery import ArchiveDiscoveryResult
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import ExtractItemsStep, TransformItemsStep
from mock_ev.entities import Archive, VaultStore
from mock_ev.generators import DatasetGenerator


def _build_metrics() -> MigrationMetrics:
    """Build a deterministic metrics object for mock EV completion tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=0.0,
        throughput_items_per_second=0.0,
        average_item_size=0,
        processed_bytes=0,
        estimated_remaining_seconds=None,
        peak_memory_usage_mb=None,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_snapshot() -> ProgressSnapshot:
    """Build a deterministic progress snapshot for mock EV completion tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=0,
        processed_items=0,
        successful_items=0,
        failed_items=0,
        skipped_items=0,
        current_archive=None,
        current_mailbox=None,
        current_item=None,
        started_at=timestamp,
        last_updated=timestamp,
    )


def _build_step_context(
    *,
    vault_stores: tuple[VaultStore, ...],
    discovery_result: ArchiveDiscoveryResult,
    current_timestamp: datetime,
) -> MigrationStepContext:
    """Build a migration step context for extraction and transformation tests."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    metrics = _build_metrics()
    progress_tracker = ProgressTracker(
        snapshot=_build_snapshot(),
        metrics=metrics,
        execution_report=ExecutionReport(
            successful_steps=0,
            failed_steps=0,
            skipped_steps=0,
            duration_seconds=0.0,
            completed=False,
            metrics=metrics,
        ),
        migration_state=MigrationState.DISCOVERING,
    )
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step="discover",
        metrics=metrics,
        progress_tracker=progress_tracker,
        state=MigrationState.DISCOVERING,
        current_timestamp=current_timestamp,
    )
    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=progress_tracker,
        state_machine=MigrationStateMachine(current_state=MigrationState.DISCOVERING),
        execution_report=progress_tracker.current_execution_report,
        discovery_result=discovery_result,
        vault_stores=vault_stores,
    )


def _archive_names(vault_stores: tuple[VaultStore, ...]) -> tuple[str, ...]:
    """Return the archive names from a deterministic dataset."""

    return tuple(archive.name for vault_store in vault_stores for archive in vault_store.archives)


def _all_archives(vault_stores: tuple[VaultStore, ...]) -> tuple[Archive, ...]:
    """Return all archives from a deterministic dataset."""

    return tuple(archive for vault_store in vault_stores for archive in vault_store.archives)


def test_mixed_dataset_contains_required_source_scenarios() -> None:
    """The mixed dataset should contain the required deterministic scenarios."""

    dataset_a = DatasetGenerator(seed=1).generate_mixed()
    dataset_b = DatasetGenerator(seed=99).generate_mixed()
    archives = _all_archives(tuple(dataset_a))

    assert dataset_a == dataset_b
    assert {archive.archive_type for archive in archives} >= {
        ArchiveType.MAILBOX,
        ArchiveType.JOURNAL,
        ArchiveType.FSA,
    }
    assert any(archive.is_orphaned for archive in archives)

    mailbox_archive = next(archive for archive in archives if archive.name == "Mailbox Archive")
    assert {
        mail_item.folder_path
        for mailbox in mailbox_archive.mailboxes
        for mail_item in mailbox.mail_items
    } >= {"/Inbox", "/Projects/Alpha", "/Sent Items"}
    assert any(
        mail_item.legal_hold
        for mailbox in mailbox_archive.mailboxes
        for mail_item in mailbox.mail_items
    )
    assert any(
        mail_item.item_type == ItemType.JOURNAL
        for archive in archives
        for journal_archive in archive.journal_archives
        for mail_item in journal_archive.mail_items
    )

    part_counter = Counter(
        content_part.part_id
        for archive in archives
        for mailbox in archive.mailboxes
        for mail_item in mailbox.mail_items
        for content_part in mail_item.content_parts
    )
    assert part_counter["sis-shared-part"] >= 2
    assert any(
        len(mail_item.content_parts) > 1
        for mailbox in mailbox_archive.mailboxes
        for mail_item in mailbox.mail_items
    )

    fsa_archive = next(archive for archive in archives if archive.archive_type == ArchiveType.FSA)
    assert fsa_archive.source_path == "/files/projects"
    assert fsa_archive.archived_files
    assert fsa_archive.archived_files[0].shortcut is not None
    assert fsa_archive.archived_files[0].shortcut.status == "broken"
    assert any(shortcut.status == "stale" for shortcut in fsa_archive.shortcuts)


def test_mock_enterprise_vault_source_adapter_flattens_journal_and_fsa_content() -> None:
    """The source adapter should expose journal items and archived files deterministically."""

    vault_stores = tuple(DatasetGenerator(seed=7).generate_mixed())
    adapter = MockEnterpriseVaultSourceAdapter(vault_stores=vault_stores)

    journal_items = adapter.stream_mail_items("Journal Archive")
    fsa_files = adapter.stream_archived_files("FSA Archive")

    assert len(journal_items) == 1
    assert journal_items[0].item_type == ItemType.JOURNAL
    assert journal_items[0].legal_hold is True
    assert journal_items[0].journal_metadata == (
        ("journal_id", "journal-2026"),
        ("envelope_id", "envelope-1"),
    )
    assert len(fsa_files) == 1
    assert fsa_files[0].file_name == "contract-1.docx"
    assert fsa_files[0].source_path == "/files/projects/contracts/contract-1.docx"

    orphaned_archive = adapter.load_archive("Orphaned Archive")
    assert orphaned_archive is not None
    assert orphaned_archive.is_orphaned is True
    assert orphaned_archive.original_owner_identifier == "orphaned.owner@example.com"


def test_extract_items_step_marks_fsa_archives_unsupported() -> None:
    """The extraction step should surface unsupported FSA archives explicitly."""

    vault_stores = tuple(DatasetGenerator(seed=13).generate_mixed())
    discovery_result = ArchiveDiscoveryResult(
        vault_store_names=tuple(vault_store.name for vault_store in vault_stores),
        archive_names=_archive_names(vault_stores),
        vault_store_count=len(vault_stores),
        archive_count=len(_archive_names(vault_stores)),
    )
    current_timestamp = datetime(2026, 1, 1, 13, 0, tzinfo=UTC)
    context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        current_timestamp=current_timestamp,
    )

    updated_context = ExtractItemsStep(vault_stores=vault_stores).extract(context)
    extraction_result = updated_context.extraction_result

    assert extraction_result is not None
    assert extraction_result.total_items == 5
    assert len(extraction_result.extracted_mail_items) == 5
    assert any(
        mail_item.item_type == ItemType.JOURNAL
        for mail_item in extraction_result.extracted_mail_items
    )
    assert extraction_result.unsupported_archives
    assert extraction_result.unsupported_archives[0].archive_type == ArchiveType.FSA
    assert any("Unsupported archive type" in warning for warning in extraction_result.warnings)
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.warnings == extraction_result.warnings


def test_transform_items_step_preserves_journal_orphan_and_legal_hold_metadata() -> None:
    """The transformation step should preserve the new source metadata fields."""

    vault_stores = tuple(DatasetGenerator(seed=21).generate_mixed())
    discovery_result = ArchiveDiscoveryResult(
        vault_store_names=tuple(vault_store.name for vault_store in vault_stores),
        archive_names=_archive_names(vault_stores),
        vault_store_count=len(vault_stores),
        archive_count=len(_archive_names(vault_stores)),
    )
    extraction_context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        current_timestamp=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
    )
    extracted_context = ExtractItemsStep(vault_stores=vault_stores).extract(extraction_context)

    transformed_context = TransformItemsStep(vault_stores=vault_stores).transform(
        extracted_context,
    )
    transformation_result = transformed_context.transformation_result

    assert transformation_result is not None
    assert len(transformation_result.transformed_documents) == 5

    document_by_identifier = {
        document.source_identifier: document
        for document in transformation_result.transformed_documents
    }

    mailbox_document = document_by_identifier["mailbox-item-2"]
    assert mailbox_document.archive_type == ArchiveType.MAILBOX
    assert mailbox_document.item_type == ItemType.EMAIL
    assert mailbox_document.folder_path == "/Projects/Alpha"
    assert mailbox_document.legal_hold is True
    assert mailbox_document.legal_hold_policy_id == "LHP-ALPHA"
    assert mailbox_document.is_orphaned is False
    assert mailbox_document.original_owner_identifier is None
    assert mailbox_document.source_path is None

    journal_document = document_by_identifier["journal-item-1"]
    assert journal_document.archive_type == ArchiveType.JOURNAL
    assert journal_document.item_type == ItemType.JOURNAL
    assert journal_document.mailbox_address is None
    assert journal_document.folder_path == "/Journal/2026"
    assert journal_document.legal_hold is True
    assert journal_document.legal_hold_policy_id == "LHP-JOURNAL"
    assert journal_document.department == "Journal"
    assert journal_document.journal_metadata == (
        ("journal_id", "journal-2026"),
        ("envelope_id", "envelope-1"),
    )

    orphaned_document = document_by_identifier["orphaned-item-1"]
    assert orphaned_document.is_orphaned is True
    assert orphaned_document.original_owner_identifier == "orphaned.owner@example.com"
    assert orphaned_document.owner_resolution_status == "orphaned"
