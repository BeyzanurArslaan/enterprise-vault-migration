"""Upload items pipeline step module.

This module defines the pipeline step responsible for uploading transformed
documents to storionX through the target port boundary. The step stays inside
the orchestration layer and only consumes target-neutral transformation data.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from application.dto import UploadResult
from domain.value_objects.identifiers import MigrationItemId
from ports import StorionXTargetPort

from ..contracts import ExecutionContext, ExecutionReport, PipelineStep, ProgressSnapshot
from ..metrics import MigrationMetrics
from ..progress_tracker import ProgressTracker
from ..state_machine import MigrationState, MigrationStateMachine
from ..step_context import MigrationStepContext
from ..transformation import TransformationResult, TransformedDocument
from ..upload import UploadBatchResult


class UploadItemsStep(PipelineStep):
    """Upload transformed documents to the target system."""

    def __init__(self, *, target_port: StorionXTargetPort) -> None:
        """Create an upload step bound to a target port implementation."""

        self._target_port = target_port

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare item upload for the current migration context."""

        return None

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute item upload for the current migration context."""

        updated_context = self.upload(self._build_step_context(context))
        if updated_context.execution_report is None:
            message = "Item upload did not produce an execution report"
            raise RuntimeError(message)

        return updated_context.execution_report

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize item upload after execution."""

        return None

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback item upload after failure."""

        return None

    def upload(self, context: MigrationStepContext) -> MigrationStepContext:
        """Upload transformed documents using the configured target port."""

        if context.transformation_result is None:
            message = "Upload requires transformation results"
            raise ValueError(message)

        started_at = context.execution_context.started_at
        completed_at = context.execution_context.current_timestamp or started_at
        uploaded_documents: list[TransformedDocument] = []
        failed_documents: list[TransformedDocument] = []
        skipped_documents: list[TransformedDocument] = []
        item_results: list[UploadResult] = []
        uploaded_document_ids: list[str] = []
        seen_source_identifiers: set[str] = set()
        current_document: TransformedDocument | None = None

        for transformed_document in context.transformation_result.transformed_documents:
            current_document = transformed_document
            item_result = self._build_item_result(
                document=transformed_document,
                success=False,
                error_message=None,
            )
            if transformed_document.source_identifier in seen_source_identifiers:
                skipped_documents.append(transformed_document)
                item_results.append(
                    replace(
                        item_result,
                        success=False,
                        target_identifier=transformed_document.source_identifier,
                        error_message="Skipped duplicate transformed document",
                    )
                )
                continue

            seen_source_identifiers.add(transformed_document.source_identifier)
            try:
                self._target_port.upload_archived_file(
                    transformed_document.source_identifier,
                    transformed_document,
                )
            except Exception as exc:  # pragma: no cover - exercised through tests
                failed_documents.append(transformed_document)
                item_results.append(
                    replace(
                        item_result,
                        success=False,
                        target_identifier=None,
                        error_message=str(exc),
                    )
                )
                continue

            uploaded_documents.append(transformed_document)
            uploaded_document_ids.append(transformed_document.source_identifier)
            item_results.append(
                replace(
                    item_result,
                    success=True,
                    target_identifier=transformed_document.source_identifier,
                    error_message=None,
                )
            )

        self._target_port.finalize_job(context.execution_context.migration_id)
        transformation_result = context.transformation_result
        upload_result = UploadBatchResult(
            uploaded_documents=tuple(uploaded_documents),
            failed_documents=tuple(failed_documents),
            skipped_documents=tuple(skipped_documents),
            uploaded_document_ids=tuple(uploaded_document_ids),
            item_results=tuple(item_results),
            started_at=started_at,
            completed_at=completed_at,
        )
        updated_state = self._resolve_state(context.state_machine)
        updated_metrics = self._resolve_metrics(
            metrics=(
                context.execution_context.metrics
                or (
                    context.progress_tracker.current_metrics
                    if context.progress_tracker is not None
                    else None
                )
            ),
            transformation_result=transformation_result,
            upload_result=upload_result,
            started_at=started_at,
            completed_at=completed_at,
        )
        updated_snapshot = self._build_snapshot(
            upload_result=upload_result,
            started_at=started_at,
            completed_at=completed_at,
            current_document=current_document,
        )
        completed = len(failed_documents) == 0
        updated_report = self._resolve_report(
            report=(
                context.execution_report
                or (
                    context.progress_tracker.current_execution_report
                    if context.progress_tracker is not None
                    else None
                )
            ),
            metrics=updated_metrics,
            upload_result=upload_result,
            started_at=started_at,
            completed_at=completed_at,
            completed=completed,
        )
        progress_tracker = self._resolve_tracker(
            tracker=context.progress_tracker,
            snapshot=updated_snapshot,
            metrics=updated_metrics,
            report=updated_report,
            migration_state=updated_state,
        )
        execution_context = replace(
            context.execution_context,
            current_step=self.__class__.__name__,
            metrics=updated_metrics,
            progress_tracker=progress_tracker,
            state=updated_state,
            current_timestamp=completed_at,
        )
        progress_tracker.update_execution_context(execution_context)
        progress_tracker.update_execution_report(updated_report)
        progress_tracker.update_metrics(updated_metrics)
        progress_tracker.update_snapshot(updated_snapshot)
        progress_tracker.update_migration_state(updated_state)

        return replace(
            context,
            execution_context=execution_context,
            progress_tracker=progress_tracker,
            state_machine=context.state_machine,
            execution_report=updated_report,
            transformation_result=transformation_result,
            upload_result=upload_result,
        )

    def _build_step_context(self, context: ExecutionContext) -> MigrationStepContext:
        """Wrap a legacy execution context in a migration step context."""

        return MigrationStepContext(
            execution_context=context,
            progress_tracker=context.progress_tracker,
            state_machine=None,
            execution_report=None,
        )

    def _build_item_result(
        self,
        *,
        document: TransformedDocument,
        success: bool,
        error_message: str | None,
    ) -> UploadResult:
        """Build a stable item-level upload result for a transformed document."""

        return UploadResult(
            item_id=MigrationItemId(uuid5(NAMESPACE_URL, document.source_identifier)),
            success=success,
            target_identifier=document.source_identifier,
            error_message=error_message,
        )

    def _build_snapshot(
        self,
        *,
        upload_result: UploadBatchResult,
        started_at: datetime,
        completed_at: datetime,
        current_document: TransformedDocument | None,
    ) -> ProgressSnapshot:
        """Build the updated progress snapshot for upload bookkeeping."""

        total_items = (
            len(upload_result.uploaded_documents)
            + len(upload_result.failed_documents)
            + len(upload_result.skipped_documents)
        )
        current_archive = current_document.archive_name if current_document is not None else None
        current_mailbox = current_document.mailbox_address if current_document is not None else None
        current_item = current_document.filename if current_document is not None else None
        return ProgressSnapshot(
            total_items=total_items,
            processed_items=total_items,
            successful_items=len(upload_result.uploaded_documents),
            failed_items=len(upload_result.failed_documents),
            skipped_items=len(upload_result.skipped_documents),
            current_archive=current_archive,
            current_mailbox=current_mailbox,
            current_item=current_item,
            started_at=started_at,
            last_updated=completed_at,
        )

    def _resolve_metrics(
        self,
        *,
        metrics: MigrationMetrics | None,
        transformation_result: TransformationResult,
        upload_result: UploadBatchResult,
        started_at: datetime,
        completed_at: datetime,
    ) -> MigrationMetrics:
        """Resolve the metrics object for the current upload state."""

        _ = transformation_result
        duration_seconds = max((completed_at - started_at).total_seconds(), 0.0)
        processed_items = (
            len(upload_result.uploaded_documents)
            + len(upload_result.failed_documents)
            + len(upload_result.skipped_documents)
        )
        uploaded_items = len(upload_result.uploaded_documents)
        failed_items = len(upload_result.failed_documents)
        skipped_items = len(upload_result.skipped_documents)
        all_documents = (
            upload_result.uploaded_documents
            + upload_result.failed_documents
            + upload_result.skipped_documents
        )
        processed_bytes = sum(document.size_bytes for document in all_documents)
        throughput = processed_items / duration_seconds if duration_seconds > 0.0 else 0.0
        average_item_size = processed_bytes // processed_items if processed_items > 0 else 0

        if metrics is not None:
            return replace(
                metrics,
                duration_seconds=duration_seconds,
                throughput_items_per_second=throughput,
                average_item_size=average_item_size,
                processed_bytes=processed_bytes,
                total_items=processed_items,
                processed_items=processed_items,
                successful_items=uploaded_items,
                failed_items=failed_items,
                skipped_items=skipped_items,
                retried_items=0,
                uploaded_items=uploaded_items,
                verification_failures=0,
                total_bytes=processed_bytes,
                started_at=started_at,
                finished_at=completed_at,
            )

        return MigrationMetrics(
            duration_seconds=duration_seconds,
            throughput_items_per_second=throughput,
            average_item_size=average_item_size,
            processed_bytes=processed_bytes,
            estimated_remaining_seconds=None,
            peak_memory_usage_mb=None,
            total_items=processed_items,
            processed_items=processed_items,
            successful_items=uploaded_items,
            failed_items=failed_items,
            skipped_items=skipped_items,
            retried_items=0,
            uploaded_items=uploaded_items,
            verification_failures=0,
            total_bytes=processed_bytes,
            started_at=started_at,
            finished_at=completed_at,
        )

    def _resolve_report(
        self,
        *,
        report: ExecutionReport | None,
        metrics: MigrationMetrics,
        upload_result: UploadBatchResult,
        started_at: datetime,
        completed_at: datetime,
        completed: bool,
    ) -> ExecutionReport:
        """Resolve the execution report for the upload step."""

        duration_seconds = max((completed_at - started_at).total_seconds(), 0.0)
        skipped_steps = len(upload_result.skipped_documents)
        if report is not None:
            return replace(
                report,
                successful_steps=1 if completed else 0,
                failed_steps=0 if completed else 1,
                skipped_steps=skipped_steps,
                duration_seconds=duration_seconds,
                completed=completed,
                metrics=metrics,
            )

        return ExecutionReport(
            successful_steps=1 if completed else 0,
            failed_steps=0 if completed else 1,
            skipped_steps=skipped_steps,
            duration_seconds=duration_seconds,
            completed=completed,
            metrics=metrics,
        )

    def _resolve_tracker(
        self,
        *,
        tracker: ProgressTracker | None,
        snapshot: ProgressSnapshot,
        metrics: MigrationMetrics,
        report: ExecutionReport,
        migration_state: MigrationState,
    ) -> ProgressTracker:
        """Return the tracker that should hold the latest upload state."""

        if tracker is not None:
            return tracker

        return ProgressTracker(
            snapshot=snapshot,
            metrics=metrics,
            execution_report=report,
            migration_state=migration_state,
        )

    def _resolve_state(
        self,
        state_machine: MigrationStateMachine | None,
    ) -> MigrationState:
        """Resolve the upload state without introducing business logic."""

        if state_machine is not None:
            if state_machine.can_transition(MigrationState.UPLOADING):
                state_machine.transition_to(MigrationState.UPLOADING)

            return state_machine.current_state

        return MigrationState.UPLOADING


__all__: list[str] = ["UploadItemsStep"]
