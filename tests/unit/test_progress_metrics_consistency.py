"""Regression tests for progress, metrics, and result consistency.

This module verifies that orchestration counters remain aligned across the
runner and the finalization step without introducing new engine abstractions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import (
    ExecutionContext,
    ExecutionReport,
    PipelineStep,
    ProgressSnapshot,
)
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import FinalizeMigrationStep
from migration_engine.transformation import TransformationResult, TransformedDocument
from migration_engine.upload import UploadBatchResult
from migration_engine.verification import VerificationResult


def _build_metrics(
    *,
    total_items: int,
    processed_items: int,
    successful_items: int,
    failed_items: int,
    skipped_items: int,
) -> MigrationMetrics:
    """Create a metrics snapshot for consistency assertions."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=2.5,
        throughput_items_per_second=2.8,
        average_item_size=512,
        processed_bytes=1024,
        estimated_remaining_seconds=None,
        peak_memory_usage_mb=None,
        total_items=total_items,
        processed_items=processed_items,
        successful_items=successful_items,
        failed_items=failed_items,
        skipped_items=skipped_items,
        retried_items=0,
        uploaded_items=successful_items,
        verification_failures=failed_items,
        total_bytes=1024,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_transformed_document(*, source_identifier: str) -> TransformedDocument:
    """Create a deterministic transformed document for finalization tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return TransformedDocument(
        source_identifier=source_identifier,
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject=f"Subject {source_identifier}",
        filename=f"{source_identifier}.eml",
        content_type="message/rfc822",
        size_bytes=256,
        checksum=source_identifier,
        sender="sender@example.com",
        recipients=("recipient@example.com",),
        cc_recipients=(),
        bcc_recipients=(),
        retention_policy="Standard",
        department="Finance",
        tags=("Archive One", "alice@example.com"),
        custom_properties=(("internet_message_id", source_identifier),),
        attachment_filenames=(),
        attachment_checksums=(),
        attachment_sizes=(),
        created_at=timestamp,
        modified_at=timestamp,
    )


class _MetricsReportingStep(PipelineStep):
    """Return a report whose metrics differ from step counts."""

    def __init__(self, report: ExecutionReport) -> None:
        """Create a step that returns the supplied execution report."""

        self._report = report

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare the step without changing shared orchestration state."""

        return None

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Return the configured execution report."""

        return self._report

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize the step without changing shared orchestration state."""

        return None

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback the step without changing shared orchestration state."""

        return None


def test_pipeline_runner_keeps_item_metrics_aligned_with_progress_snapshot() -> None:
    """The runner should preserve item-level metrics in the progress snapshot."""

    reported_metrics = _build_metrics(
        total_items=7,
        processed_items=7,
        successful_items=6,
        failed_items=1,
        skipped_items=0,
    )
    report = ExecutionReport(
        successful_steps=1,
        failed_steps=0,
        skipped_steps=0,
        duration_seconds=2.5,
        completed=True,
        metrics=reported_metrics,
    )
    runner = PipelineRunner([_MetricsReportingStep(report)])

    result = runner.run()

    assert result.success is True
    assert result.execution_report is not None
    assert result.execution_report.successful_steps == 1
    assert result.execution_report.failed_steps == 0
    assert result.execution_report.metrics is not None
    assert result.execution_report.metrics.total_items == 7
    assert result.execution_report.metrics.processed_items == 7
    assert result.execution_report.metrics.successful_items == 6
    assert result.execution_report.metrics.failed_items == 1
    assert result.execution_report.metrics.skipped_items == 0
    assert runner.progress_tracker is not None
    assert runner.progress_tracker.current_snapshot.total_items == 7
    assert runner.progress_tracker.current_snapshot.processed_items == 7
    assert runner.progress_tracker.current_snapshot.successful_items == 6
    assert runner.progress_tracker.current_snapshot.failed_items == 1
    assert runner.progress_tracker.current_execution_report == result.execution_report
    assert result.metrics == result.execution_report.metrics


def test_finalize_migration_step_keeps_result_and_tracker_consistent() -> None:
    """The finalization step should keep its result objects aligned."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=5)
    first_document = _build_transformed_document(source_identifier="message-1")
    second_document = _build_transformed_document(source_identifier="message-2")
    transformation_result = TransformationResult(
        transformed_documents=(first_document, second_document),
        skipped_items=0,
        failed_items=0,
        warnings=(),
        started_at=started_at,
        completed_at=completed_at,
    )
    upload_result = UploadBatchResult(
        uploaded_documents=(first_document,),
        failed_documents=(second_document,),
        skipped_documents=(),
        uploaded_document_ids=(first_document.source_identifier,),
        item_results=(),
        started_at=started_at,
        completed_at=completed_at,
    )
    verification_result = VerificationResult(
        verified_document_ids=(first_document.source_identifier,),
        failed_document_ids=(),
        missing_document_ids=(),
        checksum_mismatches=(),
        metadata_mismatches=(),
        verified_count=1,
        failed_count=0,
        started_at=started_at,
        completed_at=completed_at,
        warnings=(),
    )
    metrics = _build_metrics(
        total_items=2,
        processed_items=2,
        successful_items=1,
        failed_items=1,
        skipped_items=0,
    )
    report = ExecutionReport(
        successful_steps=1,
        failed_steps=0,
        skipped_steps=0,
        duration_seconds=5.0,
        completed=True,
        metrics=metrics,
    )
    progress_tracker = ProgressTracker(
        snapshot=ProgressSnapshot(
            total_items=0,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            current_archive=None,
            current_mailbox=None,
            current_item=None,
            started_at=started_at,
            last_updated=started_at,
        ),
        metrics=metrics,
        execution_report=report,
        migration_state=MigrationState.VERIFYING,
    )
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step="finalize",
        metrics=metrics,
        progress_tracker=progress_tracker,
        state=MigrationState.VERIFYING,
        current_timestamp=completed_at,
    )
    context = MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=progress_tracker,
        state_machine=MigrationStateMachine(current_state=MigrationState.VERIFYING),
        execution_report=report,
        transformation_result=transformation_result,
        upload_result=upload_result,
        verification_result=verification_result,
    )

    updated_context = FinalizeMigrationStep().finalize_migration(context)

    execution_result = updated_context.execution_result
    assert execution_result is not None
    execution_report = updated_context.execution_report
    assert execution_report is not None
    assert execution_result.success is True
    assert execution_result.execution_report == execution_report
    assert execution_result.metrics == execution_report.metrics
    assert execution_result.completed_at == completed_at
    assert execution_result.duration == timedelta(seconds=5)
    assert execution_result.warnings == ("1 items failed upload",)
    assert updated_context.progress_tracker is not None
    assert updated_context.progress_tracker.current_metrics == execution_result.metrics
    assert updated_context.progress_tracker.current_snapshot.total_items == 2
    assert updated_context.progress_tracker.current_snapshot.processed_items == 2
    assert updated_context.progress_tracker.current_snapshot.successful_items == 1
    assert updated_context.progress_tracker.current_snapshot.failed_items == 1
    assert updated_context.progress_tracker.current_snapshot.last_updated == completed_at
