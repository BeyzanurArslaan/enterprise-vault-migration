"""Regression tests for the SIS rehydration cache and transform integration."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from domain.exceptions import ValidationError
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.rehydration import RehydratedContent, SisRehydrator
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import TransformItemsStep
from mock_ev.entities import (
    Archive,
    Attachment,
    ContentPart,
    Mailbox,
    MailItem,
    RetentionPolicy,
    VaultStore,
)


def _build_retention_policy() -> RetentionPolicy:
    """Create a sample retention policy for SIS tests."""

    return RetentionPolicy(name="Standard", retention_days=30, classification="general")


def _build_content_part(part_id: str, data: bytes) -> ContentPart:
    """Create a deterministic SIS content part for tests."""

    return ContentPart(
        part_id=part_id,
        data_ref=f"sis://{part_id}",
        data=data,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _build_attachment(filename: str, size_bytes: int) -> Attachment:
    """Create a deterministic attachment for SIS tests."""

    return Attachment(
        filename=filename,
        extension="txt",
        mime_type="text/plain",
        size_bytes=size_bytes,
        checksum=f"checksum-{filename}",
    )


def _build_mail_item(*, subject: str, content_parts: tuple[ContentPart, ...]) -> MailItem:
    """Create a sample mail item with optional SIS content parts."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MailItem(
        subject=subject,
        sender="sender@example.com",
        body="legacy-body",
        received_at=timestamp,
        sent_at=timestamp,
        modified_at=timestamp,
        internet_message_id=f"message-{subject}",
        conversation_id=f"conversation-{subject}",
        message_size=128,
        retention_policy=_build_retention_policy(),
        recipients=["recipient@example.com"],
        cc_recipients=[],
        bcc_recipients=[],
        attachments=[_build_attachment(f"{subject}.txt", 16)],
        content_parts=list(content_parts),
    )


def _build_vault_store(mail_items: tuple[MailItem, ...]) -> tuple[VaultStore, Archive, Mailbox]:
    """Create a deterministic vault store hierarchy for SIS tests."""

    mailbox = Mailbox(address="alice@example.com", mail_items=list(mail_items))
    archive = Archive(name="Archive One", mailboxes=[mailbox])
    vault_store = VaultStore(name="Vault Store One", archives=[archive])
    return vault_store, archive, mailbox


def _build_metrics() -> MigrationMetrics:
    """Create a metrics object with deterministic defaults for SIS tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=0.0,
        throughput_items_per_second=0.0,
        average_item_size=0,
        processed_bytes=0,
        estimated_remaining_seconds=None,
        peak_memory_usage_mb=None,
        total_items=0,
        processed_items=0,
        successful_items=0,
        failed_items=0,
        skipped_items=0,
        retried_items=0,
        uploaded_items=0,
        verification_failures=0,
        rehydrated_items=0,
        rehydration_failures=0,
        rehydrated_bytes=0,
        sis_cache_hits=0,
        sis_cache_misses=0,
        total_bytes=0,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_snapshot() -> ProgressSnapshot:
    """Create a deterministic progress snapshot for SIS tests."""

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
    mail_items: tuple[MailItem, ...],
    current_timestamp: datetime,
) -> MigrationStepContext:
    """Create a deterministic step context for SIS integration tests."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    metrics = _build_metrics()
    progress_tracker = ProgressTracker(snapshot=_build_snapshot(), metrics=metrics)
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step="extract",
        metrics=metrics,
        progress_tracker=progress_tracker,
        state=MigrationState.EXTRACTING,
        current_timestamp=current_timestamp,
    )
    discovery_result = None
    extraction_result = None
    if len(mail_items) > 0:
        from migration_engine.discovery import ArchiveDiscoveryResult
        from migration_engine.extraction import ExtractionResult

        discovery_result = ArchiveDiscoveryResult(
            vault_store_names=("Vault Store One",),
            archive_names=("Archive One",),
            vault_store_count=1,
            archive_count=1,
        )
        extraction_result = ExtractionResult(
            discovered_archives=(vault_stores[0].archives[0],),
            extracted_mailboxes=(vault_stores[0].archives[0].mailboxes[0],),
            extracted_mail_items=mail_items,
            extracted_attachments=tuple(
                attachment for mail_item in mail_items for attachment in mail_item.attachments
            ),
            total_mailboxes=1,
            total_items=len(mail_items),
            total_attachments=len(
                tuple(
                    attachment for mail_item in mail_items for attachment in mail_item.attachments
                )
            ),
        )

    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=progress_tracker,
        state_machine=MigrationStateMachine(current_state=MigrationState.EXTRACTING),
        execution_report=ExecutionReport(
            successful_steps=0,
            failed_steps=0,
            skipped_steps=0,
            duration_seconds=0.0,
            completed=False,
            metrics=metrics,
        ),
        discovery_result=discovery_result,
        vault_stores=vault_stores,
        extraction_result=extraction_result,
    )


def test_sis_rehydrator_rebuilds_content_and_reuses_cache() -> None:
    """The rehydrator should validate parts, preserve order, and cache bytes."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at
    first_part = _build_content_part("part-1", b"Hello ")
    second_part = _build_content_part("part-2", b"world")
    mail_item = _build_mail_item(subject="Greeting", content_parts=(first_part, second_part))

    rehydrator = SisRehydrator()
    first_result = rehydrator.rehydrate(
        mail_item,
        started_at=started_at,
        completed_at=completed_at,
    )
    second_result = rehydrator.rehydrate(
        mail_item,
        started_at=started_at,
        completed_at=completed_at,
    )

    expected_bytes = b"Hello world"
    expected_checksum = hashlib.sha256(expected_bytes).hexdigest()

    assert first_result == RehydratedContent(
        source_identifier="message-Greeting",
        content_bytes=expected_bytes,
        content_parts=(first_part, second_part),
        checksum=expected_checksum,
        size_bytes=len(expected_bytes),
        started_at=started_at,
        completed_at=completed_at,
    )
    assert second_result == first_result
    assert rehydrator.rehydrated_items == 2
    assert rehydrator.rehydration_failures == 0
    assert rehydrator.rehydrated_bytes == len(expected_bytes) * 2
    assert rehydrator.cache_hits == 2
    assert rehydrator.cache_misses == 2


def test_sis_rehydrator_falls_back_to_legacy_body_when_parts_are_absent() -> None:
    """The rehydrator should preserve backward compatibility for body-only items."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    mail_item = _build_mail_item(subject="Legacy", content_parts=())
    rehydrator = SisRehydrator()

    result = rehydrator.rehydrate(
        mail_item,
        started_at=started_at,
        completed_at=started_at,
    )

    assert result.content_bytes == b"legacy-body"
    assert result.content_parts == ()
    assert result.checksum == hashlib.sha256(b"legacy-body").hexdigest()
    assert result.size_bytes == len(b"legacy-body")
    assert rehydrator.rehydrated_items == 1
    assert rehydrator.rehydration_failures == 0
    assert rehydrator.cache_hits == 0
    assert rehydrator.cache_misses == 0


def test_sis_rehydrator_rejects_checksum_mismatch() -> None:
    """The rehydrator should fail structurally when metadata does not match bytes."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    bad_part = ContentPart(
        part_id="part-1",
        data_ref="sis://part-1",
        data=b"payload",
        size_bytes=len(b"payload"),
        sha256="invalid-checksum",
    )
    mail_item = _build_mail_item(subject="Broken", content_parts=(bad_part,))
    rehydrator = SisRehydrator()

    try:
        rehydrator.rehydrate(
            mail_item,
            started_at=started_at,
            completed_at=started_at,
        )
    except ValidationError as exc:
        assert "checksum" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected the rehydrator to reject the invalid part")

    assert rehydrator.rehydration_failures == 1
    assert rehydrator.cache_hits == 0
    assert rehydrator.cache_misses == 0


def test_transform_items_step_uses_rehydrated_content_and_updates_metrics() -> None:
    """The transform step should reuse SIS content and update rehydration metrics."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at
    part = _build_content_part("part-1", b"Body")
    mail_item = _build_mail_item(subject="Message", content_parts=(part,))
    vault_store, archive, mailbox = _build_vault_store((mail_item,))
    step_context = _build_step_context(
        vault_stores=(vault_store,),
        mail_items=(mail_item,),
        current_timestamp=completed_at,
    )

    rehydrator = SisRehydrator()
    step = TransformItemsStep(vault_stores=(vault_store,), sis_rehydrator=rehydrator)
    updated_context = step.transform(step_context)

    assert updated_context.transformation_result is not None
    assert updated_context.transformation_result.failed_items == 0
    assert (
        updated_context.transformation_result.transformed_documents[0].archive_name == archive.name
    )
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.rehydrated_items == 1
    assert updated_context.execution_context.metrics.rehydration_failures == 0
    assert updated_context.execution_context.metrics.rehydrated_bytes == len(b"Body")
    assert updated_context.execution_context.metrics.sis_cache_hits == 0
    assert updated_context.execution_context.metrics.sis_cache_misses == 1
    assert rehydrator.rehydrated_items == 1
    assert rehydrator.cache_hits == 0
    assert rehydrator.cache_misses == 1
    report = updated_context.execution_report
    assert report is not None
    assert updated_context.execution_context.metrics == report.metrics
    assert report.warnings == ()
    assert updated_context.progress_tracker is not None
    assert updated_context.progress_tracker.current_migration_state == MigrationState.TRANSFORMING
    assert mailbox.address == "alice@example.com"


def test_transform_items_step_records_rehydration_failures_without_stopping_batch() -> None:
    """The transform step should keep processing after a failed SIS validation."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at
    good_part = _build_content_part("part-1", b"Good")
    bad_part = ContentPart(
        part_id="part-2",
        data_ref="sis://part-2",
        data=b"Broken",
        size_bytes=len(b"Broken"),
        sha256="invalid-checksum",
    )
    good_mail_item = _build_mail_item(subject="Good", content_parts=(good_part,))
    bad_mail_item = _build_mail_item(subject="Bad", content_parts=(bad_part,))
    vault_store, _, _ = _build_vault_store((good_mail_item, bad_mail_item))
    step_context = _build_step_context(
        vault_stores=(vault_store,),
        mail_items=(good_mail_item, bad_mail_item),
        current_timestamp=completed_at,
    )

    rehydrator = SisRehydrator()
    step = TransformItemsStep(vault_stores=(vault_store,), sis_rehydrator=rehydrator)
    updated_context = step.transform(step_context)

    assert updated_context.transformation_result is not None
    assert len(updated_context.transformation_result.transformed_documents) == 1
    assert updated_context.transformation_result.failed_items == 1
    assert updated_context.transformation_result.warnings
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.total_items == 2
    assert updated_context.execution_context.metrics.processed_items == 2
    assert updated_context.execution_context.metrics.successful_items == 1
    assert updated_context.execution_context.metrics.failed_items == 1
    assert updated_context.execution_context.metrics.rehydrated_items == 1
    assert updated_context.execution_context.metrics.rehydration_failures == 1
    assert updated_context.execution_context.metrics.sis_cache_misses == 1
    report = updated_context.execution_report
    assert report is not None
    assert report.completed is False
    assert report.failed_steps == 1
    assert report.warnings
