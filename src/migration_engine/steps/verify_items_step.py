"""Verify items pipeline step module.

This module defines the pipeline step responsible for verifying uploaded
documents against target-neutral transformed source records through the target
port boundary. The step stays inside the orchestration layer and only
coordinates verification metadata, progress updates, and structural mismatch
reporting.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from ports import StorionXTargetPort

from ..contracts import ExecutionContext, ExecutionReport, PipelineStep, ProgressSnapshot
from ..metrics import MigrationMetrics
from ..progress_tracker import ProgressTracker
from ..state_machine import MigrationState, MigrationStateMachine
from ..step_context import MigrationStepContext
from ..transformation import TransformationResult, TransformedDocument
from ..upload import UploadBatchResult
from ..verification import VerificationResult


class VerifyItemsStep(PipelineStep):
    """Verify uploaded documents against target-neutral transformed records."""

    def __init__(self, *, target_port: StorionXTargetPort) -> None:
        """Create a verification step bound to a target port implementation."""

        self._target_port = target_port

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare item verification for the current migration context."""

        return None

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute item verification for the current migration context."""

        updated_context = self.verify(self._build_step_context(context))
        if updated_context.execution_report is None:
            message = "Item verification did not produce an execution report"
            raise RuntimeError(message)

        return updated_context.execution_report

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize item verification after execution."""

        return None

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback item verification after failure."""

        return None

    def verify(self, context: MigrationStepContext) -> MigrationStepContext:
        """Verify uploaded documents against the target store."""

        if context.transformation_result is None:
            message = "Verification requires transformation results"
            raise ValueError(message)

        if context.upload_result is None:
            message = "Verification requires upload results"
            raise ValueError(message)

        dry_run_mode = context.execution_context.configuration.dry_run or any(
            result.dry_run for result in context.upload_result.item_results
        )
        started_at = context.execution_context.started_at
        completed_at = context.execution_context.current_timestamp or started_at
        verified_document_ids: list[str] = []
        failed_document_ids: list[str] = []
        missing_document_ids: list[str] = []
        checksum_mismatches: list[str] = []
        metadata_mismatches: list[str] = []
        current_document: TransformedDocument | None = None

        if not dry_run_mode:
            for transformed_document in context.upload_result.uploaded_documents:
                current_document = transformed_document
                target_document = self._target_port.get_uploaded_document(
                    transformed_document.source_identifier,
                )
                if target_document is None:
                    missing_document_ids.append(transformed_document.source_identifier)
                    failed_document_ids.append(transformed_document.source_identifier)
                    continue

                checksum_matches = target_document.checksum == transformed_document.checksum
                metadata_matches = self._document_signature(
                    target_document
                ) == self._document_signature(transformed_document)
                if checksum_matches and metadata_matches:
                    verified_document_ids.append(transformed_document.source_identifier)
                    continue

                failed_document_ids.append(transformed_document.source_identifier)
                if not checksum_matches:
                    checksum_mismatches.append(transformed_document.source_identifier)
                if not metadata_matches:
                    metadata_mismatches.append(transformed_document.source_identifier)

        verification_result = VerificationResult(
            verified_document_ids=tuple(verified_document_ids),
            failed_document_ids=tuple(failed_document_ids),
            missing_document_ids=tuple(missing_document_ids),
            checksum_mismatches=tuple(checksum_mismatches),
            metadata_mismatches=tuple(metadata_mismatches),
            verified_count=len(verified_document_ids),
            failed_count=len(failed_document_ids),
            started_at=started_at,
            completed_at=completed_at,
            warnings=(),
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
            upload_result=context.upload_result,
            verification_result=verification_result,
            started_at=started_at,
            completed_at=completed_at,
            dry_run_mode=dry_run_mode,
        )
        updated_snapshot = self._build_snapshot(
            verification_result=verification_result,
            started_at=started_at,
            completed_at=completed_at,
            current_document=current_document,
        )
        completed = verification_result.failed_count == 0
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
            verification_result=verification_result,
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
            transformation_result=context.transformation_result,
            upload_result=context.upload_result,
            verification_result=verification_result,
        )

    def _build_step_context(self, context: ExecutionContext) -> MigrationStepContext:
        """Wrap a legacy execution context in a migration step context."""

        started_at = context.started_at
        completed_at = context.current_timestamp or started_at
        transformation_result = TransformationResult(
            transformed_documents=(),
            skipped_items=0,
            failed_items=0,
            warnings=(),
            started_at=started_at,
            completed_at=completed_at,
        )
        upload_result = UploadBatchResult(
            uploaded_documents=(),
            failed_documents=(),
            skipped_documents=(),
            uploaded_document_ids=(),
            item_results=(),
            started_at=started_at,
            completed_at=completed_at,
        )
        return MigrationStepContext(
            execution_context=context,
            progress_tracker=context.progress_tracker,
            state_machine=None,
            execution_report=None,
            transformation_result=transformation_result,
            upload_result=upload_result,
        )

    def _document_signature(self, document: TransformedDocument) -> tuple[object, ...]:
        """Build a deterministic signature for comparable document metadata."""

        return (
            document.source_identifier,
            document.archive_name,
            document.mailbox_address,
            document.subject,
            document.filename,
            document.content_type,
            document.size_bytes,
            document.sender,
            document.recipients,
            document.cc_recipients,
            document.bcc_recipients,
            document.retention_policy,
            document.department,
            document.tags,
            document.custom_properties,
            document.attachment_filenames,
            document.attachment_checksums,
            document.attachment_sizes,
            document.created_at,
            document.modified_at,
        )

    def _build_snapshot(
        self,
        *,
        verification_result: VerificationResult,
        started_at: datetime,
        completed_at: datetime,
        current_document: TransformedDocument | None,
    ) -> ProgressSnapshot:
        """Build the updated progress snapshot for verification bookkeeping."""

        current_archive = current_document.archive_name if current_document is not None else None
        current_mailbox = current_document.mailbox_address if current_document is not None else None
        current_item = current_document.filename if current_document is not None else None
        return ProgressSnapshot(
            total_items=verification_result.verified_count + verification_result.failed_count,
            processed_items=verification_result.verified_count + verification_result.failed_count,
            successful_items=verification_result.verified_count,
            failed_items=verification_result.failed_count,
            skipped_items=0,
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
        upload_result: UploadBatchResult,
        verification_result: VerificationResult,
        started_at: datetime,
        completed_at: datetime,
        dry_run_mode: bool,
    ) -> MigrationMetrics:
        """Resolve the metrics object for the current verification state."""

        duration_seconds = max((completed_at - started_at).total_seconds(), 0.0)
        dry_run_items = sum(1 for result in upload_result.item_results if result.dry_run)
        if dry_run_mode:
            processed_items = len(upload_result.item_results)
            processed_bytes = sum(
                document.size_bytes for document in upload_result.skipped_documents
            )
        else:
            processed_items = len(upload_result.uploaded_documents)
            processed_bytes = sum(
                document.size_bytes for document in upload_result.uploaded_documents
            )
        throughput = processed_items / duration_seconds if duration_seconds > 0.0 else 0.0
        average_item_size = processed_bytes // processed_items if processed_items > 0 else 0

        if metrics is not None:
            if dry_run_mode:
                return replace(
                    metrics,
                    duration_seconds=duration_seconds,
                    throughput_items_per_second=throughput,
                    average_item_size=average_item_size,
                    processed_bytes=processed_bytes,
                    total_items=processed_items,
                    processed_items=processed_items,
                    started_at=started_at,
                    finished_at=completed_at,
                    uploaded_items=0,
                    verification_failures=0,
                    total_bytes=processed_bytes,
                )

            return replace(
                metrics,
                duration_seconds=duration_seconds,
                throughput_items_per_second=throughput,
                average_item_size=average_item_size,
                processed_bytes=processed_bytes,
                total_items=processed_items,
                processed_items=processed_items,
                successful_items=verification_result.verified_count,
                failed_items=verification_result.failed_count,
                skipped_items=0,
                retried_items=0,
                uploaded_items=processed_items,
                verification_failures=verification_result.failed_count,
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
            successful_items=0 if dry_run_mode else verification_result.verified_count,
            failed_items=0 if dry_run_mode else verification_result.failed_count,
            skipped_items=(len(upload_result.skipped_documents) if dry_run_mode else 0),
            retried_items=0,
            uploaded_items=0 if dry_run_mode else processed_items,
            verification_failures=0 if dry_run_mode else verification_result.failed_count,
            dry_run_items=dry_run_items,
            total_bytes=processed_bytes,
            started_at=started_at,
            finished_at=completed_at,
        )

    def _resolve_report(
        self,
        *,
        report: ExecutionReport | None,
        metrics: MigrationMetrics,
        verification_result: VerificationResult,
        started_at: datetime,
        completed_at: datetime,
        completed: bool,
    ) -> ExecutionReport:
        """Resolve the execution report for the verification step."""

        duration_seconds = max((completed_at - started_at).total_seconds(), 0.0)
        _ = verification_result
        if report is not None:
            return replace(
                report,
                successful_steps=1 if completed else 0,
                failed_steps=0 if completed else 1,
                skipped_steps=0,
                duration_seconds=duration_seconds,
                completed=completed,
                metrics=metrics,
            )

        return ExecutionReport(
            successful_steps=1 if completed else 0,
            failed_steps=0 if completed else 1,
            skipped_steps=0,
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
        """Return the tracker that should hold the latest verification state."""

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
        """Resolve the verification state without introducing business logic."""

        if state_machine is not None:
            if state_machine.can_transition(MigrationState.VERIFYING):
                state_machine.transition_to(MigrationState.VERIFYING)

            return state_machine.current_state

        return MigrationState.VERIFYING


__all__: list[str] = ["VerifyItemsStep"]
