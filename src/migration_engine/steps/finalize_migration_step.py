"""Finalize migration pipeline step module.

This module defines the pipeline step responsible for consolidating the
results from discovery, extraction, transformation, upload, and verification
into the final execution contracts. The step stays inside the orchestration
layer and only coordinates structural completion metadata.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from ..configuration import MigrationConfiguration
from ..contracts import ExecutionContext, ExecutionReport, PipelineStep, ProgressSnapshot
from ..execution_result import ExecutionResult
from ..metrics import MigrationMetrics
from ..progress_tracker import ProgressTracker
from ..reconciliation import ReconciliationResult
from ..reporting import build_execution_report_summary, resolve_final_status
from ..state_machine import MigrationState, MigrationStateMachine
from ..step_context import MigrationStepContext
from ..transformation import TransformedDocument
from ..upload import UploadBatchResult
from ..verification import VerificationResult


class FinalizeMigrationStep(PipelineStep):
    """Finalize the migration workflow and consolidate execution outcomes."""

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare migration finalization for the current execution context."""

        return None

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute migration finalization for the current execution context."""

        updated_context = self.finalize_migration(self._build_step_context(context))
        if updated_context.execution_report is None:
            message = "Migration finalization did not produce an execution report"
            raise RuntimeError(message)

        return updated_context.execution_report

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize the migration run after execution."""

        return None

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback migration finalization after failure."""

        return None

    def finalize_migration(self, context: MigrationStepContext) -> MigrationStepContext:
        """Consolidate all stage outcomes into the final execution contracts."""

        started_at = context.execution_context.started_at
        completed_at = context.execution_context.current_timestamp or started_at
        warnings = self._build_warnings(context)
        failed_execution = self._has_failed_execution(context)
        state_machine = self._resolve_state_machine(context, failed_execution=failed_execution)
        final_state = self._advance_state_machine(state_machine, failed_execution=failed_execution)
        current_document = self._resolve_current_document(context)
        reconciliation = self._resolve_reconciliation(context)
        final_metrics = self._resolve_metrics(
            metrics=(
                context.execution_context.metrics
                or (
                    context.progress_tracker.current_metrics
                    if context.progress_tracker is not None
                    else None
                )
            ),
            context=context,
            reconciliation=reconciliation,
            started_at=started_at,
            completed_at=completed_at,
        )
        final_snapshot = self._build_snapshot(
            context=context,
            started_at=started_at,
            completed_at=completed_at,
            current_document=current_document,
        )
        final_report = self._resolve_report(
            report=(
                context.execution_report
                or (
                    context.progress_tracker.current_execution_report
                    if context.progress_tracker is not None
                    else None
                )
            ),
            metrics=final_metrics,
            reconciliation=reconciliation,
            configuration=context.execution_context.configuration,
            started_at=started_at,
            completed_at=completed_at,
            failed_execution=failed_execution,
            context=context,
        )
        final_status = resolve_final_status(final_report)
        final_report = replace(final_report, final_status=final_status)
        summary = build_execution_report_summary(
            final_report,
            checkpoint_identifier=(
                context.checkpoint.checkpoint_id if context.checkpoint is not None else None
            ),
        )
        final_report = replace(final_report, summary=summary)
        execution_result = ExecutionResult(
            success=not failed_execution,
            execution_report=final_report,
            metrics=final_metrics,
            completed_at=completed_at,
            duration=completed_at - started_at,
            warnings=warnings,
            errors=self._build_errors(failed_execution=failed_execution, warnings=warnings),
        )
        progress_tracker = self._resolve_tracker(
            tracker=context.progress_tracker,
            snapshot=final_snapshot,
            metrics=final_metrics,
            report=final_report,
            migration_state=final_state,
        )
        execution_context = replace(
            context.execution_context,
            current_step=self.__class__.__name__,
            metrics=final_metrics,
            progress_tracker=progress_tracker,
            state=final_state,
            current_timestamp=completed_at,
        )
        progress_tracker.update_execution_context(execution_context)
        progress_tracker.update_execution_report(final_report)
        progress_tracker.update_metrics(final_metrics)
        progress_tracker.update_snapshot(final_snapshot)
        progress_tracker.update_migration_state(final_state)

        return replace(
            context,
            execution_context=execution_context,
            progress_tracker=progress_tracker,
            state_machine=state_machine,
            execution_report=final_report,
            execution_result=execution_result,
        )

    def _build_step_context(self, context: ExecutionContext) -> MigrationStepContext:
        """Wrap a legacy execution context in a migration step context."""

        state_machine = MigrationStateMachine(
            current_state=context.state or MigrationState.FINALIZING,
        )
        return MigrationStepContext(
            execution_context=context,
            progress_tracker=context.progress_tracker,
            state_machine=state_machine,
            execution_report=(
                context.progress_tracker.current_execution_report
                if context.progress_tracker is not None
                else None
            ),
        )

    def _has_failed_execution(self, context: MigrationStepContext) -> bool:
        """Determine whether finalization must mark the migration as failed."""

        if (
            context.state_machine is not None
            and context.state_machine.current_state == MigrationState.FAILED
        ):
            return True

        return context.execution_context.state == MigrationState.FAILED

    def _resolve_state_machine(
        self,
        context: MigrationStepContext,
        *,
        failed_execution: bool,
    ) -> MigrationStateMachine:
        """Resolve the state machine used for finalization transitions."""

        if context.state_machine is not None:
            return context.state_machine

        initial_state = context.execution_context.state or MigrationState.FINALIZING
        if failed_execution and initial_state != MigrationState.FAILED:
            initial_state = MigrationState.FAILED
        return MigrationStateMachine(current_state=initial_state)

    def _advance_state_machine(
        self,
        state_machine: MigrationStateMachine,
        *,
        failed_execution: bool,
    ) -> MigrationState:
        """Advance the migration state machine to its terminal state."""

        if failed_execution:
            if (
                state_machine.current_state != MigrationState.FAILED
                and state_machine.can_transition(MigrationState.FAILED)
            ):
                state_machine.transition_to(MigrationState.FAILED)
            return state_machine.current_state

        if (
            state_machine.current_state != MigrationState.FINALIZING
            and state_machine.can_transition(MigrationState.FINALIZING)
        ):
            state_machine.transition_to(MigrationState.FINALIZING)

        if state_machine.can_transition(MigrationState.COMPLETED):
            state_machine.transition_to(MigrationState.COMPLETED)

        return state_machine.current_state

    def _build_warnings(self, context: MigrationStepContext) -> tuple[str, ...]:
        """Build deterministic warnings from available stage results."""

        warnings: list[str] = []
        if (
            context.transformation_result is not None
            and context.transformation_result.failed_items > 0
        ):
            warnings.append(
                f"{context.transformation_result.failed_items} items failed transformation",
            )
        if context.upload_result is not None and context.upload_result.failed_documents:
            warnings.append(
                f"{len(context.upload_result.failed_documents)} items failed upload",
            )
        if context.verification_result is not None and context.verification_result.failed_count > 0:
            warnings.append(
                f"{context.verification_result.failed_count} items failed verification",
            )
        if context.upload_result is not None and context.upload_result.skipped_documents:
            warnings.append(
                f"{len(context.upload_result.skipped_documents)} items were skipped during upload",
            )
        if (
            context.transformation_result is not None
            and context.transformation_result.skipped_items > 0
        ):
            warnings.append(
                (
                    f"{context.transformation_result.skipped_items} items were "
                    "skipped during transformation"
                ),
            )

        return tuple(warnings)

    def _build_errors(
        self,
        *,
        failed_execution: bool,
        warnings: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Build terminal execution errors for a failed finalization."""

        if not failed_execution:
            return ()

        if warnings:
            return ("Migration execution failed.", *warnings)

        return ("Migration execution failed.",)

    def _resolve_reconciliation(
        self,
        context: MigrationStepContext,
    ) -> ReconciliationResult:
        """Build the final reconciliation summary for the migration run."""

        transformed_documents = (
            context.transformation_result.transformed_documents
            if context.transformation_result is not None
            else ()
        )
        upload_result = context.upload_result
        verification_result = context.verification_result
        dry_run_mode = context.execution_context.configuration.dry_run or (
            upload_result is not None
            and any(result.dry_run for result in upload_result.item_results)
        )
        expected_items = len(transformed_documents)
        uploaded_items = self._resolve_uploaded_items(upload_result)
        verified_items = (
            verification_result.verified_count if verification_result is not None else 0
        )
        idempotent_replays = self._resolve_idempotent_replays(upload_result)
        dry_run_items = self._resolve_dry_run_items(upload_result)
        checksum_mismatches = (
            verification_result.checksum_mismatches if verification_result is not None else ()
        )
        missing_items = self._resolve_missing_items(
            transformed_documents=transformed_documents,
            upload_result=upload_result,
            verification_result=verification_result,
            dry_run_mode=dry_run_mode,
        )
        unexpected_items: tuple[str, ...] = ()
        idempotent_replays = self._resolve_idempotent_replays(upload_result)
        is_reconciled = self._is_reconciled(
            expected_items=expected_items,
            uploaded_items=uploaded_items,
            verified_items=verified_items,
            idempotent_replays=idempotent_replays,
            dry_run_items=dry_run_items,
            missing_items=missing_items,
            checksum_mismatches=checksum_mismatches,
            unexpected_items=unexpected_items,
            dry_run_mode=dry_run_mode,
        )
        status = (
            "dry_run_reconciled"
            if dry_run_mode and is_reconciled
            else ("reconciled" if is_reconciled else "needs_review")
        )
        return ReconciliationResult(
            expected_items=expected_items,
            uploaded_items=uploaded_items,
            verified_items=verified_items,
            idempotent_replays=idempotent_replays,
            dry_run_items=dry_run_items,
            missing_items=missing_items,
            unexpected_items=unexpected_items,
            checksum_mismatches=checksum_mismatches,
            status=status,
            is_reconciled=is_reconciled,
        )

    def _resolve_current_document(
        self,
        context: MigrationStepContext,
    ) -> TransformedDocument | None:
        """Return the latest document available for progress bookkeeping."""

        if context.verification_result is not None and context.upload_result is not None:
            for document in reversed(context.upload_result.uploaded_documents):
                if document.source_identifier in context.verification_result.verified_document_ids:
                    return document

        if context.upload_result is not None and context.upload_result.uploaded_documents:
            return context.upload_result.uploaded_documents[-1]

        if (
            context.transformation_result is not None
            and context.transformation_result.transformed_documents
        ):
            return context.transformation_result.transformed_documents[-1]

        return None

    def _build_snapshot(
        self,
        *,
        context: MigrationStepContext,
        started_at: datetime,
        completed_at: datetime,
        current_document: TransformedDocument | None,
    ) -> ProgressSnapshot:
        """Build the final progress snapshot for migration bookkeeping."""

        total_items = self._resolve_total_items(context)
        processed_items = total_items
        successful_items = self._resolve_successful_items(context)
        failed_items = self._resolve_failed_items(context)
        skipped_items = self._resolve_skipped_items(context)
        current_archive = (
            current_document.archive_name
            if current_document is not None
            else self._current_archive_from_context(context)
        )
        current_mailbox = (
            current_document.mailbox_address
            if current_document is not None
            else self._current_mailbox_from_context(context)
        )
        current_item = (
            current_document.filename
            if current_document is not None
            else self._current_item_from_context(context)
        )
        return ProgressSnapshot(
            total_items=total_items,
            processed_items=processed_items,
            successful_items=successful_items,
            failed_items=failed_items,
            skipped_items=skipped_items,
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
        context: MigrationStepContext,
        reconciliation: ReconciliationResult,
        started_at: datetime,
        completed_at: datetime,
    ) -> MigrationMetrics:
        """Resolve the final metrics object for the migration execution."""

        total_items = self._resolve_total_items(context)
        processed_items = total_items
        successful_items = self._resolve_successful_items(context)
        failed_items = self._resolve_failed_items(context)
        skipped_items = self._resolve_skipped_items(context)
        dry_run_mode = context.execution_context.configuration.dry_run or (
            context.upload_result is not None
            and any(result.dry_run for result in context.upload_result.item_results)
        )
        uploaded_items = reconciliation.uploaded_items
        verification_failures = (
            context.verification_result.failed_count
            if context.verification_result is not None
            else 0
        )
        processed_bytes = self._resolve_processed_bytes(context)
        duration_seconds = max((completed_at - started_at).total_seconds(), 0.0)
        throughput = processed_items / duration_seconds if duration_seconds > 0.0 else 0.0
        average_item_size = processed_bytes // processed_items if processed_items > 0 else 0
        dry_run_items = reconciliation.dry_run_items
        idempotent_replays = reconciliation.idempotent_replays
        reconciled_items = (
            reconciliation.dry_run_items if dry_run_mode else reconciliation.verified_items
        )
        missing_items = len(reconciliation.missing_items)
        checksum_mismatches = len(reconciliation.checksum_mismatches)

        if metrics is not None:
            return replace(
                metrics,
                duration_seconds=duration_seconds,
                throughput_items_per_second=throughput,
                average_item_size=average_item_size,
                processed_bytes=processed_bytes,
                total_items=total_items,
                processed_items=processed_items,
                successful_items=0 if dry_run_mode else successful_items,
                failed_items=0 if dry_run_mode else failed_items,
                skipped_items=skipped_items,
                retried_items=0,
                idempotent_replays=idempotent_replays,
                reconciled_items=reconciled_items,
                missing_items=missing_items,
                checksum_mismatches=checksum_mismatches,
                uploaded_items=0 if dry_run_mode else uploaded_items,
                verification_failures=0 if dry_run_mode else verification_failures,
                dry_run_items=dry_run_items,
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
            total_items=total_items,
            processed_items=processed_items,
            successful_items=0 if dry_run_mode else successful_items,
            failed_items=0 if dry_run_mode else failed_items,
            skipped_items=skipped_items,
            retried_items=0,
            idempotent_replays=idempotent_replays,
            reconciled_items=reconciled_items,
            missing_items=missing_items,
            checksum_mismatches=checksum_mismatches,
            uploaded_items=0 if dry_run_mode else uploaded_items,
            verification_failures=0 if dry_run_mode else verification_failures,
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
        reconciliation: ReconciliationResult,
        configuration: MigrationConfiguration,
        started_at: datetime,
        completed_at: datetime,
        failed_execution: bool,
        context: MigrationStepContext,
    ) -> ExecutionReport:
        """Resolve the final execution report for the migration execution."""

        duration_seconds = max((completed_at - started_at).total_seconds(), 0.0)
        if report is not None:
            discovered_archives = (
                context.discovery_result.archive_count
                if context.discovery_result is not None
                else 0
            )
            extracted_items = (
                context.extraction_result.total_items
                if context.extraction_result is not None
                else 0
            )
            transformed_items = (
                len(context.transformation_result.transformed_documents)
                if context.transformation_result is not None
                else 0
            )
            return replace(
                report,
                successful_steps=0 if failed_execution else 1,
                failed_steps=1 if failed_execution else 0,
                skipped_steps=0,
                duration_seconds=duration_seconds,
                completed=not failed_execution,
                job_id=context.execution_context.migration_id,
                started_at=started_at,
                completed_at=completed_at,
                resumed=context.checkpoint is not None,
                checkpoint_sequence=None,
                discovered_archives=discovered_archives,
                extracted_items=extracted_items,
                transformed_items=transformed_items,
                warnings=self._build_warnings(context),
                metrics=metrics,
                reconciliation=reconciliation,
                archive_names=configuration.archive_names,
                folder_paths=configuration.folder_paths,
                start_date=configuration.start_date,
                end_date=configuration.end_date,
            )

        discovered_archives = (
            context.discovery_result.archive_count if context.discovery_result is not None else 0
        )
        extracted_items = (
            context.extraction_result.total_items if context.extraction_result is not None else 0
        )
        transformed_items = (
            len(context.transformation_result.transformed_documents)
            if context.transformation_result is not None
            else 0
        )
        return ExecutionReport(
            successful_steps=0 if failed_execution else 1,
            failed_steps=1 if failed_execution else 0,
            skipped_steps=0,
            duration_seconds=duration_seconds,
            completed=not failed_execution,
            job_id=context.execution_context.migration_id,
            started_at=started_at,
            completed_at=completed_at,
            resumed=context.checkpoint is not None,
            checkpoint_sequence=None,
            discovered_archives=discovered_archives,
            extracted_items=extracted_items,
            transformed_items=transformed_items,
            warnings=self._build_warnings(context),
            metrics=metrics,
            reconciliation=reconciliation,
            archive_names=configuration.archive_names,
            folder_paths=configuration.folder_paths,
            start_date=configuration.start_date,
            end_date=configuration.end_date,
        )

    def _resolve_uploaded_items(
        self,
        upload_result: UploadBatchResult | None,
    ) -> int:
        """Return the number of newly uploaded target documents."""

        if upload_result is None:
            return 0

        return sum(
            1
            for item_result in upload_result.item_results
            if item_result.success and not item_result.idempotent_replay and not item_result.dry_run
        )

    def _resolve_idempotent_replays(
        self,
        upload_result: UploadBatchResult | None,
    ) -> int:
        """Return the number of upload replays that reused an existing target document."""

        if upload_result is None:
            return 0

        return sum(1 for item_result in upload_result.item_results if item_result.idempotent_replay)

    def _resolve_dry_run_items(
        self,
        upload_result: UploadBatchResult | None,
    ) -> int:
        """Return the number of dry-run uploads skipped during reconciliation."""

        if upload_result is None:
            return 0

        return sum(1 for item_result in upload_result.item_results if item_result.dry_run)

    def _resolve_missing_items(
        self,
        *,
        transformed_documents: Sequence[TransformedDocument],
        upload_result: UploadBatchResult | None,
        verification_result: VerificationResult | None,
        dry_run_mode: bool,
    ) -> tuple[str, ...]:
        """Return the ordered identifiers that are missing from the target outcome."""

        if dry_run_mode:
            return ()

        missing_document_ids: set[str] = set()
        if verification_result is not None:
            missing_document_ids.update(verification_result.missing_document_ids)

        failed_upload_ids: set[str] = set()
        if upload_result is not None:
            failed_upload_ids.update(
                document.source_identifier for document in upload_result.failed_documents
            )

        missing_items: list[str] = []
        seen_missing: set[str] = set()
        for transformed_document in transformed_documents:
            source_identifier = transformed_document.source_identifier
            if source_identifier in seen_missing:
                continue

            if source_identifier in missing_document_ids or source_identifier in failed_upload_ids:
                missing_items.append(source_identifier)
                seen_missing.add(source_identifier)

        return tuple(missing_items)

    def _is_reconciled(
        self,
        *,
        expected_items: int,
        uploaded_items: int,
        verified_items: int,
        idempotent_replays: int,
        dry_run_items: int,
        missing_items: tuple[str, ...],
        checksum_mismatches: tuple[str, ...],
        unexpected_items: tuple[str, ...],
        dry_run_mode: bool,
    ) -> bool:
        """Return whether the final migration scope reconciled successfully."""

        if dry_run_mode:
            return (
                expected_items == dry_run_items
                and uploaded_items == 0
                and not missing_items
                and not checksum_mismatches
                and not unexpected_items
            )

        return (
            expected_items == verified_items
            and uploaded_items + idempotent_replays <= expected_items
            and not missing_items
            and not checksum_mismatches
            and not unexpected_items
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
        """Return the tracker that should hold the final migration state."""

        if tracker is not None:
            return tracker

        return ProgressTracker(
            snapshot=snapshot,
            metrics=metrics,
            execution_report=report,
            migration_state=migration_state,
        )

    def _resolve_total_items(self, context: MigrationStepContext) -> int:
        """Resolve the total number of items represented by the final state."""

        if context.extraction_result is not None:
            return context.extraction_result.total_items

        if context.transformation_result is not None:
            return (
                len(context.transformation_result.transformed_documents)
                + context.transformation_result.failed_items
                + context.transformation_result.skipped_items
            )

        if context.upload_result is not None:
            return (
                len(context.upload_result.uploaded_documents)
                + len(context.upload_result.failed_documents)
                + len(context.upload_result.skipped_documents)
            )

        if context.verification_result is not None:
            return (
                context.verification_result.verified_count
                + context.verification_result.failed_count
            )

        return 0

    def _resolve_successful_items(self, context: MigrationStepContext) -> int:
        """Resolve the number of successfully processed items."""

        if context.verification_result is not None:
            return context.verification_result.verified_count

        if context.upload_result is not None:
            return len(context.upload_result.uploaded_documents)

        if context.transformation_result is not None:
            return len(context.transformation_result.transformed_documents)

        if context.extraction_result is not None:
            return context.extraction_result.total_items

        return 0

    def _resolve_failed_items(self, context: MigrationStepContext) -> int:
        """Resolve the number of failed items represented by finalization."""

        failed_items = 0
        if context.transformation_result is not None:
            failed_items += context.transformation_result.failed_items
        if context.upload_result is not None:
            failed_items += len(context.upload_result.failed_documents)
        if context.verification_result is not None:
            failed_items += context.verification_result.failed_count

        return failed_items

    def _resolve_skipped_items(self, context: MigrationStepContext) -> int:
        """Resolve the number of skipped items represented by finalization."""

        skipped_items = 0
        if context.transformation_result is not None:
            skipped_items += context.transformation_result.skipped_items
        if context.upload_result is not None:
            skipped_items += len(context.upload_result.skipped_documents)

        return skipped_items

    def _resolve_processed_bytes(self, context: MigrationStepContext) -> int:
        """Resolve the processed byte count for the final metrics."""

        if context.upload_result is not None and context.upload_result.uploaded_documents:
            return sum(document.size_bytes for document in context.upload_result.uploaded_documents)

        if (
            context.transformation_result is not None
            and context.transformation_result.transformed_documents
        ):
            return sum(
                document.size_bytes
                for document in context.transformation_result.transformed_documents
            )

        return 0

    def _current_archive_from_context(self, context: MigrationStepContext) -> str | None:
        """Return the current archive name derived from stage results."""

        if context.upload_result is not None and context.upload_result.uploaded_documents:
            return context.upload_result.uploaded_documents[-1].archive_name
        if (
            context.transformation_result is not None
            and context.transformation_result.transformed_documents
        ):
            return context.transformation_result.transformed_documents[-1].archive_name
        return None

    def _current_mailbox_from_context(self, context: MigrationStepContext) -> str | None:
        """Return the current mailbox address derived from stage results."""

        if context.upload_result is not None and context.upload_result.uploaded_documents:
            return context.upload_result.uploaded_documents[-1].mailbox_address
        if (
            context.transformation_result is not None
            and context.transformation_result.transformed_documents
        ):
            return context.transformation_result.transformed_documents[-1].mailbox_address
        return None

    def _current_item_from_context(self, context: MigrationStepContext) -> str | None:
        """Return the current item name derived from stage results."""

        if context.upload_result is not None and context.upload_result.uploaded_documents:
            return context.upload_result.uploaded_documents[-1].filename
        if (
            context.transformation_result is not None
            and context.transformation_result.transformed_documents
        ):
            return context.transformation_result.transformed_documents[-1].filename
        return None


__all__: list[str] = ["FinalizeMigrationStep"]
