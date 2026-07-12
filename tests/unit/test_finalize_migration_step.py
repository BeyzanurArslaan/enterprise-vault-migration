"""Regression tests for the migration finalization step."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from application.dto import UploadResult
from domain.value_objects.identifiers import MigrationItemId
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from migration_engine.execution_result import ExecutionResult
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import FinalizeMigrationStep
from migration_engine.transformation import TransformationResult, TransformedDocument
from migration_engine.upload import UploadBatchResult
from migration_engine.verification import VerificationResult


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for finalization tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=12.0,
        throughput_items_per_second=1.0,
        average_item_size=256,
        processed_bytes=512,
        estimated_remaining_seconds=4.0,
        peak_memory_usage_mb=64.0,
        total_items=2,
        processed_items=2,
        successful_items=2,
        failed_items=0,
        skipped_items=0,
        retried_items=0,
        uploaded_items=2,
        verification_failures=0,
        total_bytes=512,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_snapshot() -> ProgressSnapshot:
    """Create a sample progress snapshot for finalization tests."""

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


def _build_transformed_document(
    *,
    source_identifier: str,
    archive_name: str,
    mailbox_address: str,
    subject: str,
    checksum: str | None = None,
    department: str = "Finance",
) -> TransformedDocument:
    """Create a deterministic transformed document for finalization tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    resolved_checksum = checksum or source_identifier
    return TransformedDocument(
        source_identifier=source_identifier,
        archive_name=archive_name,
        mailbox_address=mailbox_address,
        subject=subject,
        filename=f"{subject}.eml",
        content_type="message/rfc822",
        size_bytes=256,
        checksum=resolved_checksum,
        sender="sender@example.com",
        recipients=("recipient@example.com",),
        cc_recipients=(),
        bcc_recipients=(),
        retention_policy="Standard",
        department=department,
        tags=(archive_name, mailbox_address),
        custom_properties=(("internet_message_id", source_identifier),),
        attachment_filenames=(),
        attachment_checksums=(),
        attachment_sizes=(),
        created_at=timestamp,
        modified_at=timestamp,
    )


def _build_transformation_result(
    transformed_documents: tuple[TransformedDocument, ...],
    *,
    started_at: datetime,
    completed_at: datetime,
) -> TransformationResult:
    """Create a sample transformation result for finalization tests."""

    return TransformationResult(
        transformed_documents=transformed_documents,
        skipped_items=0,
        failed_items=0,
        warnings=(),
        started_at=started_at,
        completed_at=completed_at,
    )


def _build_upload_result(
    uploaded_documents: tuple[TransformedDocument, ...],
    *,
    failed_documents: tuple[TransformedDocument, ...] = (),
    skipped_documents: tuple[TransformedDocument, ...] = (),
    started_at: datetime,
    completed_at: datetime,
) -> UploadBatchResult:
    """Create a sample upload result for finalization tests."""

    successful_results = tuple(
        UploadResult(
            item_id=MigrationItemId(uuid5(NAMESPACE_URL, document.source_identifier)),
            success=True,
            target_identifier=document.source_identifier,
            error_message=None,
        )
        for document in uploaded_documents
    )
    failed_results = tuple(
        UploadResult(
            item_id=MigrationItemId(uuid5(NAMESPACE_URL, document.source_identifier)),
            success=False,
            target_identifier=None,
            error_message="upload failed",
        )
        for document in failed_documents
    )
    return UploadBatchResult(
        uploaded_documents=uploaded_documents,
        failed_documents=failed_documents,
        skipped_documents=skipped_documents,
        uploaded_document_ids=tuple(document.source_identifier for document in uploaded_documents),
        item_results=successful_results + failed_results,
        started_at=started_at,
        completed_at=completed_at,
    )


def _build_verification_result(
    *,
    verified_documents: tuple[TransformedDocument, ...],
    failed_document_ids: tuple[str, ...] = (),
    missing_document_ids: tuple[str, ...] = (),
    checksum_mismatches: tuple[str, ...] = (),
    metadata_mismatches: tuple[str, ...] = (),
    started_at: datetime,
    completed_at: datetime,
) -> VerificationResult:
    """Create a sample verification result for finalization tests."""

    return VerificationResult(
        verified_document_ids=tuple(document.source_identifier for document in verified_documents),
        failed_document_ids=failed_document_ids,
        missing_document_ids=missing_document_ids,
        checksum_mismatches=checksum_mismatches,
        metadata_mismatches=metadata_mismatches,
        verified_count=len(verified_documents),
        failed_count=len(failed_document_ids),
        started_at=started_at,
        completed_at=completed_at,
        warnings=(),
    )


def _build_execution_report(*, metrics: MigrationMetrics, completed: bool) -> ExecutionReport:
    """Create a sample execution report for finalization tests."""

    return ExecutionReport(
        successful_steps=1 if completed else 0,
        failed_steps=0 if completed else 1,
        skipped_steps=0,
        duration_seconds=metrics.duration_seconds,
        completed=completed,
        metrics=metrics,
    )


def _build_context(
    *,
    transformation_result: TransformationResult | None = None,
    upload_result: UploadBatchResult | None = None,
    verification_result: VerificationResult | None = None,
    report: ExecutionReport | None = None,
    state: MigrationState = MigrationState.VERIFYING,
    execution_state: MigrationState | None = None,
) -> MigrationStepContext:
    """Create a migration step context for finalization tests."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=5)
    metrics = _build_metrics()
    snapshot = _build_snapshot()
    tracker = ProgressTracker(
        snapshot=snapshot,
        metrics=metrics,
        execution_report=report,
        migration_state=state,
    )
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step="verify",
        metrics=metrics,
        progress_tracker=tracker,
        state=execution_state or state,
        current_timestamp=completed_at,
    )
    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=tracker,
        state_machine=MigrationStateMachine(current_state=state),
        execution_report=report,
        transformation_result=transformation_result,
        upload_result=upload_result,
        verification_result=verification_result,
    )


def test_finalize_migration_step_completes_successfully() -> None:
    """The step should finalize a successful migration run."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=5)
    first_document = _build_transformed_document(
        source_identifier="message-1",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Quarterly Report",
    )
    second_document = _build_transformed_document(
        source_identifier="message-2",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Annual Report",
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
    verification_result = _build_verification_result(
        verified_documents=transformed_documents,
        started_at=started_at,
        completed_at=completed_at,
    )
    context = _build_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        verification_result=verification_result,
        report=_build_execution_report(metrics=_build_metrics(), completed=False),
    )

    updated_context = FinalizeMigrationStep().finalize_migration(context)

    assert updated_context is not context
    assert context.execution_result is None
    execution_result = updated_context.execution_result
    assert execution_result is not None
    assert isinstance(execution_result, ExecutionResult)
    assert execution_result.success is True
    assert execution_result.warnings == ()
    assert updated_context.execution_context.current_step == "FinalizeMigrationStep"
    assert updated_context.execution_context.state == MigrationState.COMPLETED
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    assert progress_tracker.current_migration_state == MigrationState.COMPLETED
    assert progress_tracker.current_snapshot.total_items == 2
    assert progress_tracker.current_snapshot.successful_items == 2
    execution_report = updated_context.execution_report
    assert execution_report is not None
    assert execution_report.completed is True
    assert execution_report.failed_steps == 0
    assert execution_report.metrics == execution_result.metrics


def test_finalize_migration_step_handles_empty_context() -> None:
    """The step should finalize an empty migration without failing."""

    context = _build_context(report=None)

    updated_context = FinalizeMigrationStep().finalize_migration(context)

    execution_result = updated_context.execution_result
    assert execution_result is not None
    assert execution_result.success is True
    assert execution_result.warnings == ()
    execution_report = updated_context.execution_report
    assert execution_report is not None
    assert execution_report.completed is True
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    assert progress_tracker.current_snapshot.total_items == 0
    assert progress_tracker.current_snapshot.processed_items == 0
    assert progress_tracker.current_migration_state == MigrationState.COMPLETED


def test_finalize_migration_step_records_upload_failures_without_erasing_successes() -> None:
    """The step should preserve successful uploads when other uploads fail."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=5)
    first_document = _build_transformed_document(
        source_identifier="message-1",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Quarterly Report",
    )
    second_document = _build_transformed_document(
        source_identifier="message-2",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Annual Report",
    )
    transformation_result = _build_transformation_result(
        (first_document, second_document),
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = _build_upload_result(
        (first_document,),
        failed_documents=(second_document,),
        started_at=started_at,
        completed_at=completed_at,
    )
    verification_result = _build_verification_result(
        verified_documents=(first_document,),
        started_at=started_at,
        completed_at=completed_at,
    )
    context = _build_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        verification_result=verification_result,
        report=_build_execution_report(metrics=_build_metrics(), completed=False),
    )

    updated_context = FinalizeMigrationStep().finalize_migration(context)

    execution_result = updated_context.execution_result
    assert execution_result is not None
    assert execution_result.success is True
    assert execution_result.warnings == ("1 items failed upload",)
    execution_report = updated_context.execution_report
    assert execution_report is not None
    assert execution_report.completed is True
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    metrics = progress_tracker.current_metrics
    assert metrics is not None
    assert progress_tracker.current_snapshot.successful_items == 1
    assert progress_tracker.current_snapshot.failed_items == 1
    assert metrics.successful_items == 1
    assert metrics.failed_items == 1


def test_finalize_migration_step_records_verification_failures_without_erasing_successes() -> None:
    """The step should preserve successful verifications when other items fail."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=5)
    first_document = _build_transformed_document(
        source_identifier="message-1",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Quarterly Report",
    )
    second_document = _build_transformed_document(
        source_identifier="message-2",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Annual Report",
    )
    transformation_result = _build_transformation_result(
        (first_document, second_document),
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = _build_upload_result(
        (first_document, second_document),
        started_at=started_at,
        completed_at=completed_at,
    )
    verification_result = _build_verification_result(
        verified_documents=(first_document,),
        failed_document_ids=("message-2",),
        metadata_mismatches=("message-2",),
        started_at=started_at,
        completed_at=completed_at,
    )
    context = _build_context(
        transformation_result=transformation_result,
        upload_result=upload_result,
        verification_result=verification_result,
        report=_build_execution_report(metrics=_build_metrics(), completed=False),
    )

    updated_context = FinalizeMigrationStep().finalize_migration(context)

    execution_result = updated_context.execution_result
    assert execution_result is not None
    assert execution_result.success is True
    assert execution_result.warnings == ("1 items failed verification",)
    execution_report = updated_context.execution_report
    assert execution_report is not None
    assert execution_report.completed is True
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    metrics = progress_tracker.current_metrics
    assert metrics is not None
    assert progress_tracker.current_snapshot.successful_items == 1
    assert progress_tracker.current_snapshot.failed_items == 1
    assert metrics.verification_failures == 1


def test_finalize_migration_step_transitions_to_failed_when_context_is_failed() -> None:
    """The step should transition to failed when the execution is already failed."""

    context = _build_context(
        report=_build_execution_report(metrics=_build_metrics(), completed=False),
        state=MigrationState.FAILED,
        execution_state=MigrationState.FAILED,
    )

    updated_context = FinalizeMigrationStep().finalize_migration(context)

    execution_result = updated_context.execution_result
    assert execution_result is not None
    assert execution_result.success is False
    assert execution_result.errors[0] == "Migration execution failed."
    execution_report = updated_context.execution_report
    assert execution_report is not None
    assert execution_report.completed is False
    assert updated_context.execution_context.state == MigrationState.FAILED
    progress_tracker = updated_context.progress_tracker
    assert progress_tracker is not None
    assert progress_tracker.current_migration_state == MigrationState.FAILED


def test_finalize_migration_step_is_deterministic_and_uses_existing_contracts() -> None:
    """The step should produce deterministic outputs with the existing contracts."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=5)
    first_document = _build_transformed_document(
        source_identifier="message-1",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Quarterly Report",
    )
    second_document = _build_transformed_document(
        source_identifier="message-2",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Annual Report",
    )
    base_context = _build_context(
        transformation_result=_build_transformation_result(
            (first_document, second_document),
            started_at=started_at,
            completed_at=completed_at,
        ),
        upload_result=_build_upload_result(
            (first_document, second_document),
            started_at=started_at,
            completed_at=completed_at,
        ),
        verification_result=_build_verification_result(
            verified_documents=(first_document, second_document),
            started_at=started_at,
            completed_at=completed_at,
        ),
        report=_build_execution_report(metrics=_build_metrics(), completed=False),
    )
    second_context = _build_context(
        transformation_result=base_context.transformation_result,
        upload_result=base_context.upload_result,
        verification_result=base_context.verification_result,
        report=_build_execution_report(metrics=_build_metrics(), completed=False),
    )

    first_result = FinalizeMigrationStep().finalize_migration(base_context)
    second_result = FinalizeMigrationStep().finalize_migration(second_context)

    first_execution_result = first_result.execution_result
    second_execution_result = second_result.execution_result
    assert first_execution_result == second_execution_result
    assert first_result.execution_report == second_result.execution_report
    assert first_execution_result is not None
    assert first_execution_result.success is True
    assert Path("src/migration_engine/finalization/finalization_result.py").exists() is False


def test_finalize_migration_step_has_no_direct_mock_storionx_imports() -> None:
    """The finalization step should remain decoupled from mock storionX imports."""

    source_text = Path("src/migration_engine/steps/finalize_migration_step.py").read_text()

    assert "mock_storionx" not in source_text
    assert "src.mock_storionx" not in source_text


def test_ports_and_migration_engine_import_without_circular_failure() -> None:
    """The ports package and migration engine package should import cleanly."""

    importlib.import_module("ports.storionx_target_port")
    importlib.import_module("migration_engine.steps.finalize_migration_step")
