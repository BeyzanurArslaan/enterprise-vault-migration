"""Regression tests for the item verification migration step."""

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
from migration_engine.steps import VerifyItemsStep
from migration_engine.transformation import TransformationResult, TransformedDocument
from migration_engine.upload import UploadBatchResult
from ports import StorionXTargetPort


class _RecordingTargetPort(StorionXTargetPort):
    """Record verification lookups for step assertions."""

    def __init__(self, *, documents: dict[str, TransformedDocument] | None = None) -> None:
        """Create a recording target port with optional uploaded documents."""

        self.documents = documents or {}
        self.lookup_calls: list[str] = []

    def create_archive(self, archive_id: str) -> str:
        """Record archive creation calls."""

        return archive_id

    def upload_mail_item(self, mail_item_id: str, payload: object) -> object:
        """Record mail item uploads."""

        return payload

    def upload_attachment(self, attachment_id: str, payload: object) -> object:
        """Record attachment uploads."""

        return payload

    def upload_archived_file(self, archived_file_id: str, payload: object) -> object:
        """Record document uploads."""

        return payload

    def finalize_job(self, job_id: str) -> str:
        """Record job finalization calls."""

        return job_id

    def get_uploaded_document(self, document_id: str) -> TransformedDocument | None:
        """Return a configured uploaded document for verification tests."""

        self.lookup_calls.append(document_id)
        return self.documents.get(document_id)


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for verification tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=7.5,
        throughput_items_per_second=1.0,
        average_item_size=256,
        processed_bytes=768,
        estimated_remaining_seconds=5.0,
        peak_memory_usage_mb=96.0,
        total_items=3,
        processed_items=3,
        successful_items=3,
        failed_items=0,
        skipped_items=0,
        retried_items=0,
        uploaded_items=3,
        verification_failures=0,
        total_bytes=768,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_snapshot() -> ProgressSnapshot:
    """Create a sample progress snapshot for verification tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=3,
        processed_items=2,
        successful_items=2,
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
    checksum: str | None = None,
    department: str = "Finance",
) -> TransformedDocument:
    """Create a deterministic transformed document for verification tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    attachment_filenames = tuple(
        f"{subject}-{index}.txt" for index, _size in enumerate(attachment_sizes, start=1)
    )
    attachment_checksums = tuple(f"checksum-{filename}" for filename in attachment_filenames)
    resolved_checksum = checksum or source_identifier
    return TransformedDocument(
        source_identifier=source_identifier,
        archive_name=archive_name,
        mailbox_address=mailbox_address,
        subject=subject,
        filename=f"{subject}.eml",
        content_type="message/rfc822",
        size_bytes=message_size + sum(attachment_sizes),
        checksum=resolved_checksum,
        sender="sender@example.com",
        recipients=("recipient@example.com",),
        cc_recipients=("cc@example.com",),
        bcc_recipients=(),
        retention_policy="Standard",
        department=department,
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
    """Create a sample transformation result for verification tests."""

    return TransformationResult(
        transformed_documents=transformed_documents,
        skipped_items=0,
        failed_items=0,
        warnings=(),
        started_at=started_at,
        completed_at=completed_at,
    )


def _build_upload_result(
    transformed_documents: tuple[TransformedDocument, ...],
    *,
    started_at: datetime,
    completed_at: datetime,
) -> UploadBatchResult:
    """Create a sample upload result for verification tests."""

    item_results = tuple(
        UploadResult(
            item_id=MigrationItemId(uuid5(NAMESPACE_URL, document.source_identifier)),
            success=True,
            target_identifier=document.source_identifier,
            error_message=None,
        )
        for document in transformed_documents
    )
    return UploadBatchResult(
        uploaded_documents=transformed_documents,
        failed_documents=(),
        skipped_documents=(),
        uploaded_document_ids=tuple(
            document.source_identifier for document in transformed_documents
        ),
        item_results=item_results,
        started_at=started_at,
        completed_at=completed_at,
    )


def _build_step_context(
    *,
    transformation_result: TransformationResult,
    upload_result: UploadBatchResult,
    current_timestamp: datetime,
    tracker: ProgressTracker | None = None,
    report: ExecutionReport | None = None,
    state: MigrationState = MigrationState.UPLOADING,
) -> MigrationStepContext:
    """Create a migration step context for verification tests."""

    started_at = transformation_result.started_at
    assert started_at is not None
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step="upload",
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
        upload_result=upload_result,
    )


def _build_documents() -> tuple[TransformedDocument, ...]:
    """Create a deterministic transformed document dataset for verification tests."""

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
            source_identifier="message-B1-1",
            archive_name="Archive B1",
            mailbox_address="bob@example.com",
            subject="B1-1",
            message_size=130,
            attachment_sizes=(20, 30),
        ),
        _build_transformed_document(
            source_identifier="message-C1-1",
            archive_name="Archive C1",
            mailbox_address="carol@example.com",
            subject="C1-1",
            message_size=150,
            attachment_sizes=(),
        ),
    )


def test_verify_items_step_verifies_uploaded_documents_and_updates_shared_state() -> None:
    """The step should verify uploaded documents and update orchestration state."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=6)
    documents = _build_documents()
    transformation_result = _build_transformation_result(
        documents,
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = _build_upload_result(
        documents,
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
        migration_state=MigrationState.UPLOADING,
    )
    target_port = _RecordingTargetPort(
        documents={document.source_identifier: document for document in documents}
    )
    context = _build_step_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        current_timestamp=completed_at,
        tracker=tracker,
    )

    updated_context = VerifyItemsStep(target_port=target_port).verify(context)

    assert updated_context.verification_result is not None
    assert updated_context.verification_result.verified_document_ids == (
        "message-A1-1",
        "message-B1-1",
        "message-C1-1",
    )
    assert updated_context.verification_result.failed_document_ids == ()
    assert updated_context.verification_result.verified_count == 3
    assert updated_context.verification_result.failed_count == 0
    assert updated_context.execution_context.current_step == "VerifyItemsStep"
    assert updated_context.execution_context.current_timestamp == completed_at
    assert updated_context.execution_context.state == MigrationState.VERIFYING
    assert updated_context.progress_tracker is tracker
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    metrics = progress_tracker.current_metrics
    assert metrics is not None
    assert progress_tracker.current_snapshot.successful_items == 3
    assert metrics.verification_failures == 0
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.completed is True
    assert updated_context.execution_report.failed_steps == 0
    assert updated_context.transformation_result == transformation_result
    assert updated_context.upload_result == upload_result
    assert target_port.lookup_calls == [
        "message-A1-1",
        "message-B1-1",
        "message-C1-1",
    ]


def test_verify_items_step_handles_empty_upload_result() -> None:
    """The step should handle an empty upload batch without failing."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=1)
    transformation_result = _build_transformation_result(
        (),
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = _build_upload_result(
        (),
        started_at=started_at,
        completed_at=completed_at,
    )
    tracker = ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics())
    context = _build_step_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        current_timestamp=completed_at,
        tracker=tracker,
    )

    updated_context = VerifyItemsStep(target_port=_RecordingTargetPort()).verify(context)

    assert updated_context.verification_result is not None
    assert updated_context.verification_result.verified_document_ids == ()
    assert updated_context.verification_result.failed_document_ids == ()
    assert updated_context.verification_result.verified_count == 0
    assert updated_context.verification_result.failed_count == 0
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    metrics = progress_tracker.current_metrics
    assert metrics is not None
    assert progress_tracker.current_snapshot.total_items == 0
    assert progress_tracker.current_snapshot.processed_items == 0
    assert metrics.total_items == 0
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.completed is True
    assert updated_context.execution_report.failed_steps == 0


def test_verify_items_step_records_multiple_document_verification_in_order() -> None:
    """The step should verify documents in deterministic upload order."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=4)
    documents = _build_documents()
    transformation_result = _build_transformation_result(
        documents,
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = _build_upload_result(
        documents,
        started_at=started_at,
        completed_at=completed_at,
    )
    context = _build_step_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        current_timestamp=completed_at,
    )
    target_port = _RecordingTargetPort(
        documents={document.source_identifier: document for document in documents}
    )

    updated_context = VerifyItemsStep(target_port=target_port).verify(context)

    assert target_port.lookup_calls == [
        "message-A1-1",
        "message-B1-1",
        "message-C1-1",
    ]
    assert updated_context.verification_result is not None
    assert updated_context.verification_result.verified_document_ids == (
        "message-A1-1",
        "message-B1-1",
        "message-C1-1",
    )


def test_verify_items_step_records_missing_target_document() -> None:
    """The step should report missing uploaded documents structurally."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=5)
    documents = _build_documents()
    transformation_result = _build_transformation_result(
        documents,
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = _build_upload_result(
        documents,
        started_at=started_at,
        completed_at=completed_at,
    )
    target_port = _RecordingTargetPort(
        documents={
            documents[0].source_identifier: documents[0],
            documents[2].source_identifier: documents[2],
        }
    )
    context = _build_step_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        current_timestamp=completed_at,
    )

    updated_context = VerifyItemsStep(target_port=target_port).verify(context)

    assert updated_context.verification_result is not None
    assert updated_context.verification_result.verified_document_ids == (
        "message-A1-1",
        "message-C1-1",
    )
    assert updated_context.verification_result.missing_document_ids == ("message-B1-1",)
    assert updated_context.verification_result.failed_document_ids == ("message-B1-1",)
    assert updated_context.verification_result.failed_count == 1
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.completed is False
    assert updated_context.execution_report.failed_steps == 1


def test_verify_items_step_records_checksum_mismatch() -> None:
    """The step should report checksum mismatches structurally."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=3)
    document = _build_transformed_document(
        source_identifier="message-1",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Quarterly Report",
        message_size=2048,
        attachment_sizes=(512,),
    )
    transformation_result = _build_transformation_result(
        (document,),
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = _build_upload_result(
        (document,),
        started_at=started_at,
        completed_at=completed_at,
    )
    target_document = replace(document, checksum="different-checksum")
    context = _build_step_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        current_timestamp=completed_at,
    )
    target_port = _RecordingTargetPort(documents={document.source_identifier: target_document})

    updated_context = VerifyItemsStep(target_port=target_port).verify(context)

    assert updated_context.verification_result is not None
    assert updated_context.verification_result.verified_document_ids == ()
    assert updated_context.verification_result.checksum_mismatches == ("message-1",)
    assert updated_context.verification_result.metadata_mismatches == ()
    assert updated_context.verification_result.failed_document_ids == ("message-1",)
    assert updated_context.verification_result.failed_count == 1


def test_verify_items_step_records_metadata_mismatch() -> None:
    """The step should report metadata mismatches structurally."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=3)
    document = _build_transformed_document(
        source_identifier="message-1",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Quarterly Report",
        message_size=2048,
        attachment_sizes=(512,),
    )
    transformation_result = _build_transformation_result(
        (document,),
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = _build_upload_result(
        (document,),
        started_at=started_at,
        completed_at=completed_at,
    )
    target_document = replace(document, department="Legal")
    context = _build_step_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        current_timestamp=completed_at,
    )
    target_port = _RecordingTargetPort(documents={document.source_identifier: target_document})

    updated_context = VerifyItemsStep(target_port=target_port).verify(context)

    assert updated_context.verification_result is not None
    assert updated_context.verification_result.verified_document_ids == ()
    assert updated_context.verification_result.checksum_mismatches == ()
    assert updated_context.verification_result.metadata_mismatches == ("message-1",)
    assert updated_context.verification_result.failed_document_ids == ("message-1",)
    assert updated_context.verification_result.failed_count == 1


def test_verify_items_step_preserves_successful_verification_on_partial_failure() -> None:
    """The step should keep successful verification results when another item fails."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=5)
    first_document = _build_transformed_document(
        source_identifier="message-1",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Quarterly Report",
        message_size=2048,
        attachment_sizes=(512,),
    )
    second_document = _build_transformed_document(
        source_identifier="message-2",
        archive_name="Archive Two",
        mailbox_address="bob@example.com",
        subject="Annual Report",
        message_size=1024,
        attachment_sizes=(),
    )
    transformed_documents = (first_document, second_document)
    transformation_result = _build_transformation_result(
        transformed_documents,
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = _build_upload_result(
        transformed_documents,
        started_at=started_at,
        completed_at=completed_at,
    )
    target_port = _RecordingTargetPort(documents={first_document.source_identifier: first_document})
    context = _build_step_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        current_timestamp=completed_at,
    )

    updated_context = VerifyItemsStep(target_port=target_port).verify(context)

    assert updated_context.verification_result is not None
    assert updated_context.verification_result.verified_document_ids == ("message-1",)
    assert updated_context.verification_result.failed_document_ids == ("message-2",)
    assert updated_context.verification_result.missing_document_ids == ("message-2",)
    assert updated_context.verification_result.verified_count == 1
    assert updated_context.verification_result.failed_count == 1
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    metrics = progress_tracker.current_metrics
    assert metrics is not None
    assert metrics.successful_items == 1
    assert metrics.failed_items == 1
    assert metrics.verification_failures == 1
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.completed is False
    assert updated_context.execution_report.failed_steps == 1


def test_verify_items_step_has_no_direct_mock_storionx_imports() -> None:
    """The verification step should remain decoupled from mock storionX imports."""

    source_text = Path("src/migration_engine/steps/verify_items_step.py").read_text()

    assert "mock_storionx" not in source_text
    assert "src.mock_storionx" not in source_text
