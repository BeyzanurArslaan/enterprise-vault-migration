"""Regression tests for the item extraction migration step."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from migration_engine.discovery import ArchiveDiscoveryResult
from migration_engine.extraction import ExtractionResult
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import ExtractItemsStep
from mock_ev.entities import (
    Archive,
    Attachment,
    Mailbox,
    MailItem,
    RetentionPolicy,
    VaultStore,
)


def _build_retention_policy() -> RetentionPolicy:
    """Create a sample retention policy for extraction tests."""

    return RetentionPolicy(
        name="Standard",
        retention_days=30,
        classification="general",
    )


def _build_attachment(filename: str, size_bytes: int) -> Attachment:
    """Create a sample attachment for extraction tests."""

    return Attachment(
        filename=filename,
        extension="txt",
        mime_type="text/plain",
        size_bytes=size_bytes,
        checksum=f"checksum-{filename}",
    )


def _build_mail_item(
    *,
    subject: str,
    message_size: int,
    attachment_sizes: tuple[int, ...],
    folder_path: str = "/Inbox",
    sent_at: datetime | None = None,
) -> MailItem:
    """Create a sample mail item for extraction tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    resolved_sent_at = sent_at or timestamp
    attachments = [
        _build_attachment(filename=f"{subject}-{index}.txt", size_bytes=size_bytes)
        for index, size_bytes in enumerate(attachment_sizes, start=1)
    ]
    return MailItem(
        subject=subject,
        sender="sender@example.com",
        body="Body",
        received_at=timestamp,
        sent_at=resolved_sent_at,
        modified_at=timestamp,
        internet_message_id=f"message-{subject}",
        conversation_id=f"conversation-{subject}",
        message_size=message_size,
        retention_policy=_build_retention_policy(),
        attachments=attachments,
        folder_path=folder_path,
    )


def _build_mailbox(address: str, mail_items: tuple[MailItem, ...]) -> Mailbox:
    """Create a sample mailbox for extraction tests."""

    return Mailbox(address=address, mail_items=list(mail_items))


def _build_archive(name: str, mailboxes: tuple[Mailbox, ...]) -> Archive:
    """Create a sample archive for extraction tests."""

    return Archive(name=name, mailboxes=list(mailboxes))


def _build_vault_store(name: str, archives: tuple[Archive, ...]) -> VaultStore:
    """Create a sample vault store for extraction tests."""

    return VaultStore(name=name, archives=list(archives))


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for extraction tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=3.0,
        throughput_items_per_second=1.5,
        average_item_size=256,
        processed_bytes=512,
        estimated_remaining_seconds=9.0,
        peak_memory_usage_mb=128.0,
        total_items=10,
        processed_items=4,
        successful_items=3,
        failed_items=1,
        skipped_items=2,
        retried_items=1,
        uploaded_items=0,
        verification_failures=1,
        total_bytes=1024,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_snapshot() -> ProgressSnapshot:
    """Create a sample progress snapshot for extraction tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=10,
        processed_items=4,
        successful_items=3,
        failed_items=1,
        skipped_items=2,
        current_archive="seed-archive",
        current_mailbox="seed-mailbox",
        current_item="seed-item",
        started_at=timestamp,
        last_updated=timestamp,
    )


def _build_step_context(
    *,
    vault_stores: tuple[VaultStore, ...],
    discovery_result: ArchiveDiscoveryResult,
    current_timestamp: datetime,
    configuration: MigrationConfiguration | None = None,
    tracker: ProgressTracker | None = None,
    report: ExecutionReport | None = None,
    state: MigrationState = MigrationState.DISCOVERING,
) -> MigrationStepContext:
    """Create a migration step context for extraction tests."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=configuration or MigrationConfiguration(),
        started_at=started_at,
        current_step="discover",
        metrics=_build_metrics(),
        progress_tracker=tracker,
        state=state,
        current_timestamp=current_timestamp,
    )
    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=tracker,
        state_machine=MigrationStateMachine(current_state=state),
        execution_report=report,
        discovery_result=discovery_result,
        vault_stores=vault_stores,
    )


def _build_dataset() -> tuple[tuple[VaultStore, ...], ArchiveDiscoveryResult]:
    """Create a deterministic mixed dataset for extraction tests."""

    archive_a1 = _build_archive(
        "Archive A1",
        (
            _build_mailbox(
                "alice@example.com",
                (
                    _build_mail_item(
                        subject="A1-1",
                        message_size=100,
                        attachment_sizes=(10,),
                    ),
                    _build_mail_item(
                        subject="A1-2",
                        message_size=120,
                        attachment_sizes=(),
                    ),
                ),
            ),
            _build_mailbox("empty@example.com", ()),
        ),
    )
    archive_a2 = _build_archive("Archive A2", ())
    archive_b1 = _build_archive(
        "Archive B1",
        (
            _build_mailbox(
                "bob@example.com",
                (
                    _build_mail_item(
                        subject="B1-1",
                        message_size=130,
                        attachment_sizes=(20, 30),
                    ),
                ),
            ),
        ),
    )
    vault_stores = (
        _build_vault_store("Vault Store A", (archive_a1, archive_a2)),
        _build_vault_store("Vault Store B", (archive_b1,)),
    )
    discovery_result = ArchiveDiscoveryResult(
        vault_store_names=("Vault Store A", "Vault Store B"),
        archive_names=("Archive A1", "Archive A2", "Archive B1"),
        vault_store_count=2,
        archive_count=3,
    )
    return vault_stores, discovery_result


def test_extract_items_step_extracts_content_and_updates_shared_state() -> None:
    """The step should extract content and update orchestration state."""

    vault_stores, discovery_result = _build_dataset()
    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    finished_at = started_at + timedelta(seconds=6)
    tracker = ProgressTracker(
        snapshot=_build_snapshot(),
        metrics=_build_metrics(),
        execution_report=ExecutionReport(
            successful_steps=1,
            failed_steps=0,
            skipped_steps=0,
            duration_seconds=3.0,
            completed=True,
            metrics=_build_metrics(),
        ),
        migration_state=MigrationState.DISCOVERING,
    )
    context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        current_timestamp=finished_at,
        tracker=tracker,
    )

    step = ExtractItemsStep()
    updated_context = step.extract(context)

    expected_result = ExtractionResult(
        discovered_archives=tuple(vault_stores[0].archives + vault_stores[1].archives),
        extracted_mailboxes=(
            vault_stores[0].archives[0].mailboxes[0],
            vault_stores[0].archives[0].mailboxes[1],
            vault_stores[1].archives[0].mailboxes[0],
        ),
        extracted_mail_items=(
            vault_stores[0].archives[0].mailboxes[0].mail_items[0],
            vault_stores[0].archives[0].mailboxes[0].mail_items[1],
            vault_stores[1].archives[0].mailboxes[0].mail_items[0],
        ),
        extracted_attachments=(
            vault_stores[0].archives[0].mailboxes[0].mail_items[0].attachments[0],
            vault_stores[1].archives[0].mailboxes[0].mail_items[0].attachments[0],
            vault_stores[1].archives[0].mailboxes[0].mail_items[0].attachments[1],
        ),
        total_mailboxes=3,
        total_items=3,
        total_attachments=3,
    )

    assert updated_context.discovery_result == discovery_result
    assert updated_context.vault_stores == vault_stores
    assert updated_context.extraction_result == expected_result
    assert updated_context.execution_context.current_step == "ExtractItemsStep"
    assert updated_context.execution_context.state == MigrationState.EXTRACTING
    assert updated_context.execution_context.current_timestamp == finished_at
    assert updated_context.state_machine is not None
    assert updated_context.state_machine.current_state == MigrationState.EXTRACTING
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.completed is True
    assert updated_context.execution_report.successful_steps == 1
    assert updated_context.execution_report.failed_steps == 0
    assert updated_context.execution_report.skipped_steps == 0
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.duration_seconds == 6.0
    assert updated_context.execution_context.metrics.throughput_items_per_second == 0.5
    assert updated_context.execution_context.metrics.average_item_size == 136
    assert updated_context.execution_context.metrics.processed_bytes == 410
    assert updated_context.execution_context.metrics.total_items == 3
    assert updated_context.execution_context.metrics.processed_items == 3
    assert updated_context.execution_context.metrics.successful_items == 3
    assert updated_context.execution_context.metrics.failed_items == 0
    assert updated_context.execution_context.metrics.skipped_items == 0
    assert updated_context.execution_context.metrics.retried_items == 0
    assert updated_context.execution_context.metrics.uploaded_items == 0
    assert updated_context.execution_context.metrics.verification_failures == 0
    assert updated_context.execution_context.metrics.total_bytes == 410
    assert updated_context.execution_context.metrics.started_at == started_at
    assert updated_context.execution_context.metrics.finished_at == finished_at
    assert updated_context.execution_report.metrics == updated_context.execution_context.metrics
    assert updated_context.progress_tracker is tracker
    assert updated_context.progress_tracker.current_migration_state == MigrationState.EXTRACTING
    assert updated_context.progress_tracker.current_snapshot.total_items == 3
    assert updated_context.progress_tracker.current_snapshot.processed_items == 3
    assert updated_context.progress_tracker.current_snapshot.successful_items == 3
    assert updated_context.progress_tracker.current_snapshot.failed_items == 0
    assert updated_context.progress_tracker.current_snapshot.skipped_items == 0
    assert updated_context.progress_tracker.current_snapshot.current_archive == "Archive B1"
    assert updated_context.progress_tracker.current_snapshot.current_mailbox == "bob@example.com"
    assert updated_context.progress_tracker.current_snapshot.current_item == "B1-1"
    assert (
        updated_context.progress_tracker.current_execution_context
        is updated_context.execution_context
    )
    assert (
        updated_context.progress_tracker.current_execution_report
        is updated_context.execution_report
    )


def test_extract_items_step_is_deterministic_for_same_input() -> None:
    """The step should produce the same output for the same runtime input."""

    vault_stores, discovery_result = _build_dataset()
    finished_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC) + timedelta(seconds=6)

    first_context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        current_timestamp=finished_at,
        tracker=ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics()),
    )
    second_context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        current_timestamp=finished_at,
        tracker=ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics()),
    )

    first_result = ExtractItemsStep().extract(first_context)
    second_result = ExtractItemsStep().extract(second_context)

    assert first_result.extraction_result == second_result.extraction_result
    assert first_result.execution_report == second_result.execution_report
    assert first_result.execution_context.metrics == second_result.execution_context.metrics


def test_extract_items_step_applies_folder_and_date_filters() -> None:
    """The step should filter mail items by folder path and sent date."""

    inbox_before = _build_mail_item(
        subject="inbox-before",
        message_size=100,
        attachment_sizes=(),
        folder_path="/Inbox",
        sent_at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
    )
    nested_inbox_match = _build_mail_item(
        subject="nested-match",
        message_size=120,
        attachment_sizes=(10,),
        folder_path="/Inbox/Projects",
        sent_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    sent_after_window = _build_mail_item(
        subject="after-window",
        message_size=140,
        attachment_sizes=(),
        folder_path="/Archive",
        sent_at=datetime(2026, 1, 1, 18, 0, tzinfo=UTC),
    )
    archive = _build_archive(
        "Archive A1",
        (
            _build_mailbox("alice@example.com", (inbox_before, nested_inbox_match)),
            _build_mailbox("bob@example.com", (sent_after_window,)),
        ),
    )
    vault_stores = (_build_vault_store("Vault Store A", (archive,)),)
    discovery_result = ArchiveDiscoveryResult(
        vault_store_names=("Vault Store A",),
        archive_names=("Archive A1",),
        vault_store_count=1,
        archive_count=1,
    )
    configuration = MigrationConfiguration(
        folder_paths=("/Inbox",),
        start_date=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        end_date=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
    )
    context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        current_timestamp=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
        configuration=configuration,
        tracker=ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics()),
    )

    updated_context = ExtractItemsStep().extract(context)

    assert updated_context.extraction_result is not None
    assert updated_context.extraction_result.total_items == 1
    assert updated_context.extraction_result.extracted_mail_items == (nested_inbox_match,)
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.filtered_archives == 0
    assert updated_context.execution_context.metrics.filtered_items == 2
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.archive_names == configuration.archive_names
    assert updated_context.execution_report.folder_paths == configuration.folder_paths
    assert updated_context.execution_report.start_date == configuration.start_date
    assert updated_context.execution_report.end_date == configuration.end_date
