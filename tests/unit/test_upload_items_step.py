"""Regression tests for the item upload migration step."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from application.dto import UploadResult
from domain.value_objects.identifiers import MigrationItemId
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import UploadItemsStep
from migration_engine.transformation import TransformationResult, TransformedDocument
from migration_engine.upload import UploadBatchResult
from ports import StorionXTargetPort


class _RecordingTargetPort(StorionXTargetPort):
    """Record upload calls for upload step assertions."""

    def __init__(self, *, fail_on_identifier: str | None = None) -> None:
        """Create a recording target port with an optional failure trigger."""

        self.fail_on_identifier = fail_on_identifier
        self.calls: list[tuple[str, TransformedDocument]] = []

    def create_archive(self, archive_id: str) -> str:
        """Record archive creation calls."""

        return archive_id

    def upload_mail_item(self, mail_item_id: str, payload: object) -> object:
        """Record mail item uploads."""

        return self.upload_archived_file(mail_item_id, payload)

    def upload_attachment(self, attachment_id: str, payload: object) -> object:
        """Record attachment uploads."""

        return self.upload_archived_file(attachment_id, payload)

    def upload_archived_file(
        self,
        archived_file_id: str,
        payload: object,
    ) -> UploadResult:
        """Record document uploads and optionally simulate a failure."""

        if not isinstance(payload, TransformedDocument):
            message = "Unexpected payload"
            raise TypeError(message)

        self.calls.append((archived_file_id, payload))
        if archived_file_id == self.fail_on_identifier:
            return UploadResult(
                item_id=MigrationItemId(value=uuid5(NAMESPACE_URL, payload.source_identifier)),
                success=False,
                target_identifier=None,
                error_message=f"upload failed for {archived_file_id}",
                idempotent_replay=False,
            )

        return UploadResult(
            item_id=MigrationItemId(value=uuid5(NAMESPACE_URL, payload.source_identifier)),
            success=True,
            target_identifier=payload.source_identifier,
            error_message=None,
            idempotent_replay=False,
        )

    def finalize_job(self, job_id: str) -> str:
        """Record job finalization calls."""

        return job_id

    def get_uploaded_document(self, document_id: str) -> TransformedDocument | None:
        """Return no uploaded documents for upload step tests."""

        return None


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for upload tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=5.0,
        throughput_items_per_second=1.0,
        average_item_size=100,
        processed_bytes=300,
        estimated_remaining_seconds=4.0,
        peak_memory_usage_mb=64.0,
        total_items=3,
        processed_items=3,
        successful_items=3,
        failed_items=0,
        skipped_items=0,
        retried_items=0,
        uploaded_items=3,
        verification_failures=0,
        total_bytes=300,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_snapshot() -> ProgressSnapshot:
    """Create a sample progress snapshot for upload tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=3,
        processed_items=3,
        successful_items=3,
        failed_items=0,
        skipped_items=0,
        current_archive="archive-1",
        current_mailbox="mailbox-1",
        current_item="item-1",
        started_at=timestamp,
        last_updated=timestamp,
    )


def _build_transformed_document(
    *,
    source_identifier: str,
    archive_name: str,
    mailbox_address: str,
    subject: str,
    message_size: int,
    attachment_sizes: tuple[int, ...],
) -> TransformedDocument:
    """Create a sample transformed document for upload tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    attachment_filenames = tuple(
        f"{subject}-{index}.txt" for index, _size in enumerate(attachment_sizes, start=1)
    )
    attachment_checksums = tuple(f"checksum-{filename}" for filename in attachment_filenames)
    return TransformedDocument(
        source_identifier=source_identifier,
        archive_name=archive_name,
        mailbox_address=mailbox_address,
        subject=subject,
        filename=f"{subject}.eml",
        content_type="message/rfc822",
        size_bytes=message_size + sum(attachment_sizes),
        checksum=source_identifier,
        sender="sender@example.com",
        recipients=("recipient@example.com",),
        cc_recipients=("cc@example.com",),
        bcc_recipients=(),
        retention_policy="Standard",
        department="Finance",
        tags=(archive_name, mailbox_address, f"conversation-{subject}"),
        custom_properties=(
            ("internet_message_id", source_identifier),
            ("message_size", str(message_size)),
            ("attachment_count", str(len(attachment_sizes))),
        ),
        attachment_filenames=attachment_filenames,
        attachment_checksums=attachment_checksums,
        attachment_sizes=attachment_sizes,
        created_at=timestamp,
        modified_at=timestamp,
    )


def _build_transformation_result(
    transformed_documents: tuple[TransformedDocument, ...],
    *,
    started_at: datetime,
    completed_at: datetime,
) -> TransformationResult:
    """Create a sample transformation result for upload tests."""

    return TransformationResult(
        transformed_documents=transformed_documents,
        skipped_items=0,
        failed_items=0,
        warnings=(),
        started_at=started_at,
        completed_at=completed_at,
    )


def _build_step_context(
    *,
    transformation_result: TransformationResult,
    current_timestamp: datetime,
    tracker: ProgressTracker | None = None,
    report: ExecutionReport | None = None,
    state: MigrationState = MigrationState.TRANSFORMING,
) -> MigrationStepContext:
    """Create a migration step context for upload tests."""

    started_at = transformation_result.started_at
    assert started_at is not None
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step="transform",
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
        transformation_result=transformation_result,
    )


def _build_documents() -> tuple[TransformedDocument, ...]:
    """Create a deterministic transformed document dataset for upload tests."""

    return (
        _build_transformed_document(
            source_identifier="message-A1-1",
            archive_name="Archive A1",
            mailbox_address="alice@example.com",
            subject="A1-1",
            message_size=100,
            attachment_sizes=(10,),
        ),
        _build_transformed_document(
            source_identifier="message-A1-2",
            archive_name="Archive A1",
            mailbox_address="alice@example.com",
            subject="A1-2",
            message_size=120,
            attachment_sizes=(),
        ),
        _build_transformed_document(
            source_identifier="message-B1-1",
            archive_name="Archive B1",
            mailbox_address="bob@example.com",
            subject="B1-1",
            message_size=130,
            attachment_sizes=(20, 30),
        ),
    )


def test_upload_items_step_uploads_documents_and_updates_shared_state() -> None:
    """The step should upload transformed documents and update orchestration state."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=6)
    transformation_result = _build_transformation_result(
        _build_documents(),
        started_at=started_at,
        completed_at=completed_at,
    )
    tracker = ProgressTracker(
        snapshot=_build_snapshot(),
        metrics=_build_metrics(),
        execution_report=ExecutionReport(
            successful_steps=1,
            failed_steps=0,
            skipped_steps=0,
            duration_seconds=5.0,
            completed=True,
            metrics=_build_metrics(),
        ),
        migration_state=MigrationState.TRANSFORMING,
    )
    context = _build_step_context(
        transformation_result=transformation_result,
        current_timestamp=completed_at,
        tracker=tracker,
    )
    target_port = _RecordingTargetPort()

    updated_context = UploadItemsStep(target_port=target_port).upload(context)

    expected_results = tuple(
        UploadResult(
            item_id=MigrationItemId(uuid5(NAMESPACE_URL, document.source_identifier)),
            success=True,
            target_identifier=document.source_identifier,
            error_message=None,
        )
        for document in transformation_result.transformed_documents
    )

    assert target_port.calls == [
        (document.source_identifier, document)
        for document in transformation_result.transformed_documents
    ]
    assert updated_context.transformation_result == transformation_result
    assert updated_context.upload_result == UploadBatchResult(
        uploaded_documents=transformation_result.transformed_documents,
        failed_documents=(),
        skipped_documents=(),
        uploaded_document_ids=tuple(
            document.source_identifier for document in transformation_result.transformed_documents
        ),
        item_results=expected_results,
        started_at=started_at,
        completed_at=completed_at,
    )
    assert updated_context.execution_context.current_step == "UploadItemsStep"
    assert updated_context.execution_context.state == MigrationState.UPLOADING
    assert updated_context.execution_context.current_timestamp == completed_at
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
    assert updated_context.execution_context.metrics.uploaded_items == 3
    assert updated_context.execution_context.metrics.verification_failures == 0
    assert updated_context.execution_context.metrics.total_bytes == 410
    assert updated_context.execution_context.metrics.started_at == started_at
    assert updated_context.execution_context.metrics.finished_at == completed_at
    assert updated_context.execution_report.metrics == updated_context.execution_context.metrics
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is tracker
    assert progress_tracker is not None
    assert progress_tracker.current_migration_state == MigrationState.UPLOADING
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


def test_upload_items_step_handles_empty_transformation_result() -> None:
    """The step should handle an empty transformation result without failing."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=1)
    transformation_result = _build_transformation_result(
        (),
        started_at=started_at,
        completed_at=completed_at,
    )
    tracker = ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics())
    context = _build_step_context(
        transformation_result=transformation_result,
        current_timestamp=completed_at,
        tracker=tracker,
    )
    target_port = _RecordingTargetPort()

    updated_context = UploadItemsStep(target_port=target_port).upload(context)

    assert updated_context.upload_result == UploadBatchResult(
        uploaded_documents=(),
        failed_documents=(),
        skipped_documents=(),
        uploaded_document_ids=(),
        item_results=(),
        started_at=started_at,
        completed_at=completed_at,
    )
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.total_items == 0
    assert updated_context.execution_context.metrics.processed_items == 0
    assert updated_context.execution_context.metrics.successful_items == 0
    assert updated_context.execution_context.metrics.failed_items == 0
    assert updated_context.execution_context.metrics.skipped_items == 0
    assert updated_context.execution_context.metrics.uploaded_items == 0
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


def test_upload_items_step_records_partial_failure_without_losing_successes() -> None:
    """The step should keep successful results when one upload fails."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=5)
    transformation_result = _build_transformation_result(
        _build_documents(),
        started_at=started_at,
        completed_at=completed_at,
    )
    tracker = ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics())
    context = _build_step_context(
        transformation_result=transformation_result,
        current_timestamp=completed_at,
        tracker=tracker,
    )
    target_port = _RecordingTargetPort(fail_on_identifier="message-A1-2")

    updated_context = UploadItemsStep(target_port=target_port).upload(context)

    assert updated_context.upload_result is not None
    assert updated_context.upload_result.uploaded_document_ids == ("message-A1-1", "message-B1-1")
    assert updated_context.upload_result.uploaded_documents == (
        transformation_result.transformed_documents[0],
        transformation_result.transformed_documents[2],
    )
    assert updated_context.upload_result.failed_documents == (
        transformation_result.transformed_documents[1],
    )
    assert updated_context.upload_result.skipped_documents == ()
    assert len(updated_context.upload_result.item_results) == 3
    assert updated_context.upload_result.item_results[0].success is True
    assert updated_context.upload_result.item_results[1].success is False
    assert (
        updated_context.upload_result.item_results[1].error_message
        == "upload failed for message-A1-2"
    )
    assert updated_context.upload_result.item_results[2].success is True
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.completed is False
    assert updated_context.execution_report.successful_steps == 0
    assert updated_context.execution_report.failed_steps == 1
    assert updated_context.execution_report.skipped_steps == 0
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.total_items == 3
    assert updated_context.execution_context.metrics.processed_items == 3
    assert updated_context.execution_context.metrics.successful_items == 2
    assert updated_context.execution_context.metrics.failed_items == 1
    assert updated_context.execution_context.metrics.skipped_items == 0
    assert updated_context.execution_context.metrics.uploaded_items == 2
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    assert progress_tracker.current_snapshot.total_items == 3
    assert progress_tracker.current_snapshot.processed_items == 3
    assert progress_tracker.current_snapshot.successful_items == 2
    assert progress_tracker.current_snapshot.failed_items == 1
    assert progress_tracker.current_snapshot.skipped_items == 0
    assert progress_tracker.current_snapshot.current_item == "B1-1.eml"


def test_upload_items_step_is_deterministic_for_same_input() -> None:
    """The step should produce the same output for the same runtime input."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=6)
    first_context = _build_step_context(
        transformation_result=_build_transformation_result(
            _build_documents(),
            started_at=started_at,
            completed_at=completed_at,
        ),
        current_timestamp=completed_at,
        tracker=ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics()),
    )
    second_context = _build_step_context(
        transformation_result=_build_transformation_result(
            _build_documents(),
            started_at=started_at,
            completed_at=completed_at,
        ),
        current_timestamp=completed_at,
        tracker=ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics()),
    )

    first_result = UploadItemsStep(target_port=_RecordingTargetPort()).upload(first_context)
    second_result = UploadItemsStep(target_port=_RecordingTargetPort()).upload(second_context)

    assert first_result.upload_result == second_result.upload_result
    assert first_result.execution_report == second_result.execution_report
    assert first_result.execution_context.metrics == second_result.execution_context.metrics


def test_upload_items_step_skips_target_port_during_dry_run() -> None:
    """Dry-run uploads should skip the target boundary and remain neutral."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=6)
    transformation_result = _build_transformation_result(
        _build_documents()[:1],
        started_at=started_at,
        completed_at=completed_at,
    )
    context = _build_step_context(
        transformation_result=transformation_result,
        current_timestamp=completed_at,
        tracker=ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics()),
    )
    dry_run_context = replace(
        context,
        execution_context=replace(
            context.execution_context,
            configuration=MigrationConfiguration(dry_run=True),
        ),
    )
    target_port = _RecordingTargetPort()

    updated_context = UploadItemsStep(target_port=target_port).upload(dry_run_context)

    assert target_port.calls == []
    assert updated_context.upload_result is not None
    assert updated_context.upload_result.uploaded_documents == ()
    assert updated_context.upload_result.failed_documents == ()
    assert updated_context.upload_result.skipped_documents == (
        transformation_result.transformed_documents[0],
    )
    assert updated_context.upload_result.item_results[0].dry_run is True
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.dry_run_items == 1
    assert updated_context.execution_context.metrics.uploaded_items == 0
    assert updated_context.execution_context.metrics.idempotent_replays == 0
    assert updated_context.execution_context.metrics.skipped_items == 1


def test_migration_engine_upload_boundary_avoids_direct_mock_storionx_imports() -> None:
    """The migration engine upload boundary should not import mock storionX."""

    repository_root = Path(__file__).resolve().parents[2]
    transform_source = (
        repository_root / "src/migration_engine/steps/transform_items_step.py"
    ).read_text()
    upload_source = (
        repository_root / "src/migration_engine/steps/upload_items_step.py"
    ).read_text()
    transformation_source = (
        repository_root / "src/migration_engine/transformation/transformed_document.py"
    ).read_text()

    assert "mock_storionx" not in transform_source
    assert "mock_storionx" not in upload_source
    assert "mock_storionx" not in transformation_source
