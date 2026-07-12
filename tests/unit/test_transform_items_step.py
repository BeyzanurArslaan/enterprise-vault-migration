"""Regression tests for the item transformation migration step."""

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
from migration_engine.steps import TransformItemsStep
from migration_engine.transformation import TransformationResult, TransformedDocument
from mock_ev.entities import Archive, Attachment, Mailbox, MailItem, RetentionPolicy, VaultStore


def _build_retention_policy() -> RetentionPolicy:
    """Create a sample retention policy for transformation tests."""

    return RetentionPolicy(
        name="Standard",
        retention_days=30,
        classification="general",
    )


def _build_attachment(filename: str, size_bytes: int) -> Attachment:
    """Create a sample attachment for transformation tests."""

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
    recipients: tuple[str, ...] = (),
    cc_recipients: tuple[str, ...] = (),
    bcc_recipients: tuple[str, ...] = (),
) -> MailItem:
    """Create a sample mail item for transformation tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    attachments = [
        _build_attachment(filename=f"{subject}-{index}.txt", size_bytes=size_bytes)
        for index, size_bytes in enumerate(attachment_sizes, start=1)
    ]
    return MailItem(
        subject=subject,
        sender="sender@example.com",
        body="Body",
        received_at=timestamp,
        sent_at=timestamp,
        modified_at=timestamp,
        internet_message_id=f"message-{subject}",
        conversation_id=f"conversation-{subject}",
        message_size=message_size,
        retention_policy=_build_retention_policy(),
        recipients=list(recipients),
        cc_recipients=list(cc_recipients),
        bcc_recipients=list(bcc_recipients),
        attachments=attachments,
    )


def _build_mailbox(address: str, mail_items: tuple[MailItem, ...]) -> Mailbox:
    """Create a sample mailbox for transformation tests."""

    return Mailbox(address=address, mail_items=list(mail_items))


def _build_archive(name: str, mailboxes: tuple[Mailbox, ...]) -> Archive:
    """Create a sample archive for transformation tests."""

    return Archive(name=name, mailboxes=list(mailboxes))


def _build_vault_store(name: str, archives: tuple[Archive, ...]) -> VaultStore:
    """Create a sample vault store for transformation tests."""

    return VaultStore(name=name, archives=list(archives))


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for transformation tests."""

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
    """Create a sample progress snapshot for transformation tests."""

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
    extraction_result: ExtractionResult,
    current_timestamp: datetime,
    tracker: ProgressTracker | None = None,
    report: ExecutionReport | None = None,
    state: MigrationState = MigrationState.EXTRACTING,
) -> MigrationStepContext:
    """Create a migration step context for transformation tests."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step="extract",
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
        extraction_result=extraction_result,
    )


def _build_dataset() -> tuple[
    tuple[VaultStore, ...],
    ArchiveDiscoveryResult,
    ExtractionResult,
]:
    """Create a deterministic mixed dataset for transformation tests."""

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
                        recipients=("alice@target.test",),
                        cc_recipients=("manager@example.com",),
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
                        recipients=("bob@target.test",),
                        bcc_recipients=("audit@example.com",),
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
    extraction_result = ExtractionResult(
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
    return vault_stores, discovery_result, extraction_result


def test_transform_items_step_transforms_items_and_updates_shared_state() -> None:
    """The step should transform items and update orchestration state."""

    vault_stores, discovery_result, extraction_result = _build_dataset()
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
        migration_state=MigrationState.EXTRACTING,
    )
    context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        extraction_result=extraction_result,
        current_timestamp=finished_at,
        tracker=tracker,
    )

    step = TransformItemsStep(vault_stores=vault_stores)
    updated_context = step.transform(context)

    expected_documents = (
        TransformedDocument(
            source_identifier="message-A1-1",
            archive_name="Archive A1",
            mailbox_address="alice@example.com",
            subject="A1-1",
            filename="A1-1.eml",
            content_type="message/rfc822",
            size_bytes=110,
            checksum="message-A1-1",
            sender="sender@example.com",
            recipients=("alice@target.test",),
            cc_recipients=("manager@example.com",),
            bcc_recipients=(),
            retention_policy="Standard",
            department="Example",
            tags=("Archive A1", "alice@example.com", "conversation-A1-1"),
            custom_properties=(
                ("internet_message_id", "message-A1-1"),
                ("message_size", "100"),
                ("attachment_count", "1"),
            ),
            attachment_filenames=("A1-1-1.txt",),
            attachment_checksums=("checksum-A1-1-1.txt",),
            attachment_sizes=(10,),
            created_at=started_at,
            modified_at=started_at,
        ),
        TransformedDocument(
            source_identifier="message-A1-2",
            archive_name="Archive A1",
            mailbox_address="alice@example.com",
            subject="A1-2",
            filename="A1-2.eml",
            content_type="message/rfc822",
            size_bytes=120,
            checksum="message-A1-2",
            sender="sender@example.com",
            recipients=(),
            cc_recipients=(),
            bcc_recipients=(),
            retention_policy="Standard",
            department="Example",
            tags=("Archive A1", "alice@example.com", "conversation-A1-2"),
            custom_properties=(
                ("internet_message_id", "message-A1-2"),
                ("message_size", "120"),
                ("attachment_count", "0"),
            ),
            attachment_filenames=(),
            attachment_checksums=(),
            attachment_sizes=(),
            created_at=started_at,
            modified_at=started_at,
        ),
        TransformedDocument(
            source_identifier="message-B1-1",
            archive_name="Archive B1",
            mailbox_address="bob@example.com",
            subject="B1-1",
            filename="B1-1.eml",
            content_type="message/rfc822",
            size_bytes=180,
            checksum="message-B1-1",
            sender="sender@example.com",
            recipients=("bob@target.test",),
            cc_recipients=(),
            bcc_recipients=("audit@example.com",),
            retention_policy="Standard",
            department="Example",
            tags=("Archive B1", "bob@example.com", "conversation-B1-1"),
            custom_properties=(
                ("internet_message_id", "message-B1-1"),
                ("message_size", "130"),
                ("attachment_count", "2"),
            ),
            attachment_filenames=("B1-1-1.txt", "B1-1-2.txt"),
            attachment_checksums=("checksum-B1-1-1.txt", "checksum-B1-1-2.txt"),
            attachment_sizes=(20, 30),
            created_at=started_at,
            modified_at=started_at,
        ),
    )

    expected_result = TransformationResult(
        transformed_documents=expected_documents,
        skipped_items=0,
        failed_items=0,
        warnings=(),
        started_at=started_at,
        completed_at=finished_at,
    )

    assert updated_context.discovery_result == discovery_result
    assert updated_context.vault_stores == vault_stores
    assert updated_context.extraction_result == extraction_result
    assert updated_context.transformation_result == expected_result
    assert updated_context.execution_context.current_step == "TransformItemsStep"
    assert updated_context.execution_context.state == MigrationState.TRANSFORMING
    assert updated_context.execution_context.current_timestamp == finished_at
    assert updated_context.state_machine is not None
    assert updated_context.state_machine.current_state == MigrationState.TRANSFORMING
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
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is tracker
    assert progress_tracker is not None
    assert progress_tracker.current_migration_state == MigrationState.TRANSFORMING
    assert progress_tracker.current_snapshot.total_items == 3
    assert progress_tracker.current_snapshot.processed_items == 3
    assert progress_tracker.current_snapshot.successful_items == 3
    assert progress_tracker.current_snapshot.failed_items == 0
    assert progress_tracker.current_snapshot.skipped_items == 0
    assert progress_tracker.current_snapshot.current_archive == "Archive B1"
    assert progress_tracker.current_snapshot.current_mailbox == "bob@example.com"
    assert progress_tracker.current_snapshot.current_item == "B1-1.eml"
    assert progress_tracker.current_execution_context is updated_context.execution_context
    assert progress_tracker.current_execution_report is updated_context.execution_report


def test_transform_items_step_handles_empty_extraction() -> None:
    """The step should handle an empty extraction result without failing."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=1)
    vault_stores = (_build_vault_store("Vault Store A", (_build_archive("Archive A1", ()),)),)
    discovery_result = ArchiveDiscoveryResult(
        vault_store_names=("Vault Store A",),
        archive_names=("Archive A1",),
        vault_store_count=1,
        archive_count=1,
    )
    extraction_result = ExtractionResult(
        discovered_archives=(vault_stores[0].archives[0],),
        extracted_mailboxes=(),
        extracted_mail_items=(),
        extracted_attachments=(),
        total_mailboxes=0,
        total_items=0,
        total_attachments=0,
    )
    tracker = ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics())
    context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        extraction_result=extraction_result,
        current_timestamp=completed_at,
        tracker=tracker,
    )

    updated_context = TransformItemsStep(vault_stores=vault_stores).transform(context)

    assert updated_context.transformation_result == TransformationResult(
        transformed_documents=(),
        skipped_items=0,
        failed_items=0,
        warnings=(),
        started_at=started_at,
        completed_at=completed_at,
    )
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.total_items == 0
    assert updated_context.execution_context.metrics.processed_items == 0
    assert updated_context.execution_context.metrics.successful_items == 0
    assert updated_context.execution_context.metrics.failed_items == 0
    assert updated_context.execution_context.metrics.skipped_items == 0
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    assert progress_tracker.current_snapshot.total_items == 0
    assert progress_tracker.current_snapshot.processed_items == 0
    assert progress_tracker.current_snapshot.successful_items == 0
    assert progress_tracker.current_snapshot.failed_items == 0
    assert progress_tracker.current_snapshot.skipped_items == 0
    assert progress_tracker.current_snapshot.current_archive is None
    assert progress_tracker.current_snapshot.current_mailbox is None
    assert progress_tracker.current_snapshot.current_item is None


def test_transform_items_step_is_deterministic_for_same_input() -> None:
    """The step should produce the same output for the same runtime input."""

    vault_stores, discovery_result, extraction_result = _build_dataset()
    finished_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC) + timedelta(seconds=6)

    first_context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        extraction_result=extraction_result,
        current_timestamp=finished_at,
        tracker=ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics()),
    )
    second_context = _build_step_context(
        vault_stores=vault_stores,
        discovery_result=discovery_result,
        extraction_result=extraction_result,
        current_timestamp=finished_at,
        tracker=ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics()),
    )

    first_result = TransformItemsStep(vault_stores=vault_stores).transform(first_context)
    second_result = TransformItemsStep(vault_stores=vault_stores).transform(second_context)

    assert first_result.transformation_result == second_result.transformation_result
    assert first_result.execution_report == second_result.execution_report
    assert first_result.execution_context.metrics == second_result.execution_context.metrics
