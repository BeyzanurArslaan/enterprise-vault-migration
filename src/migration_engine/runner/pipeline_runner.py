"""Pipeline runner module for the migration engine execution layer.

This module defines the runner that coordinates registered pipeline steps with
execution state, progress tracking, metrics, and final reporting.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from ..configuration import MigrationConfiguration
from ..context import MigrationContext
from ..contracts import ExecutionContext, ExecutionReport, PipelineStep, ProgressSnapshot
from ..execution_result import ExecutionResult
from ..metrics import MigrationMetrics
from ..pipeline import MigrationPipeline
from ..progress_tracker import ProgressTracker
from ..state_machine import MigrationState, MigrationStateMachine
from .step_registry import StepRegistry


class PipelineRunner:
    """Coordinate pipeline steps, execution state, and execution outcomes."""

    def __init__(
        self,
        steps: Sequence[PipelineStep],
        *,
        pipeline: MigrationPipeline | None = None,
        context: MigrationContext | None = None,
    ) -> None:
        """Create a runner configured with ordered pipeline steps."""

        self.step_registry = StepRegistry(steps)
        self.steps: tuple[PipelineStep, ...] = self.step_registry.resolve()
        self.pipeline = pipeline
        self.context = context
        self.state_machine = MigrationStateMachine(current_state=MigrationState.CREATED)
        self.progress_tracker: ProgressTracker | None = None
        self.execution_context: ExecutionContext | None = None
        self.execution_report: ExecutionReport | None = None
        self.execution_result: ExecutionResult | None = None
        self.metrics: MigrationMetrics | None = None

    def initialize(self) -> ExecutionContext:
        """Prepare the runner before pipeline execution begins."""

        if self.execution_context is not None:
            return self.execution_context

        self.steps = self.step_registry.resolve()
        started_at = self._current_timestamp()
        self.state_machine.transition_to(MigrationState.INITIALIZING)

        progress_tracker = ProgressTracker(
            snapshot=self._build_initial_snapshot(started_at),
            migration_state=self.state_machine.current_state,
        )
        execution_context = ExecutionContext(
            migration_id=f"migration-{uuid4().hex}",
            configuration=MigrationConfiguration(),
            started_at=started_at,
            current_step=None,
            metrics=self.metrics,
            progress_tracker=progress_tracker,
            state=self.state_machine.current_state,
            current_timestamp=started_at,
        )
        progress_tracker.update_execution_context(execution_context)

        self.progress_tracker = progress_tracker
        self.execution_context = execution_context
        return execution_context

    def run(self) -> ExecutionResult:
        """Execute the configured pipeline steps in order."""

        execution_context = self.initialize()
        self.steps = self.step_registry.resolve()

        successful_steps = 0
        failed_steps = 0
        skipped_steps = 0
        latest_metrics = self.metrics
        current_context = execution_context
        completed_steps: list[PipelineStep] = []
        errors: list[str] = []

        for step in self.steps:
            step_state = self._step_state(step)
            if step_state is not None and self.state_machine.can_transition(step_state):
                self.state_machine.transition_to(step_state)

            current_context = self._advance_context(
                current_context,
                current_step=step.__class__.__name__,
                current_state=self.state_machine.current_state,
                current_timestamp=self._current_timestamp(),
                metrics=latest_metrics,
            )

            try:
                step.prepare(current_context)
                step_report = step.execute(current_context)

                successful_steps += step_report.successful_steps
                failed_steps += step_report.failed_steps
                skipped_steps += step_report.skipped_steps
                if step_report.metrics is not None:
                    latest_metrics = step_report.metrics

                step_timestamp = self._current_timestamp()
                current_context = self._advance_context(
                    current_context,
                    current_step=step.__class__.__name__,
                    current_state=self.state_machine.current_state,
                    current_timestamp=step_timestamp,
                    metrics=latest_metrics,
                )
                cumulative_metrics = self._resolve_metrics(
                    latest_metrics=latest_metrics,
                    started_at=execution_context.started_at,
                    finished_at=step_timestamp,
                )
                cumulative_report = self._build_execution_report(
                    successful_steps=successful_steps,
                    failed_steps=failed_steps,
                    skipped_steps=skipped_steps,
                    started_at=execution_context.started_at,
                    finished_at=step_timestamp,
                    metrics=cumulative_metrics,
                    completed=False,
                )
                self._sync_tracker(
                    context=current_context,
                    current_timestamp=step_timestamp,
                    metrics=cumulative_metrics,
                    report=cumulative_report,
                )
                if not self._is_successful(step_report):
                    message = f"{step.__class__.__name__} did not complete successfully"
                    raise RuntimeError(message)

                step.finalize(current_context)
                completed_steps.append(step)
            except Exception as exc:
                errors.append(str(exc))
                failure_timestamp = self._current_timestamp()
                failure_state = MigrationState.FAILED
                self.state_machine.transition_to(failure_state)
                failure_context = self._advance_context(
                    current_context,
                    current_step=step.__class__.__name__,
                    current_state=failure_state,
                    current_timestamp=failure_timestamp,
                    metrics=latest_metrics,
                )
                failure_metrics = self._resolve_metrics(
                    latest_metrics=latest_metrics,
                    started_at=execution_context.started_at,
                    finished_at=failure_timestamp,
                )
                failure_report = self._build_execution_report(
                    successful_steps=successful_steps,
                    failed_steps=failed_steps,
                    skipped_steps=skipped_steps,
                    started_at=execution_context.started_at,
                    finished_at=failure_timestamp,
                    metrics=failure_metrics,
                    completed=False,
                )
                self._rollback_steps(
                    completed_steps=completed_steps,
                    current_step=step,
                    context=failure_context,
                )
                self._sync_tracker(
                    context=failure_context,
                    current_timestamp=failure_timestamp,
                    metrics=failure_metrics,
                    report=failure_report,
                )
                return self._build_result(
                    success=False,
                    report=failure_report,
                    metrics=failure_metrics,
                    started_at=execution_context.started_at,
                    completed_at=failure_timestamp,
                    errors=tuple(errors),
                )

        completion_timestamp = self._current_timestamp()
        self.state_machine.transition_to(MigrationState.COMPLETED)
        final_metrics = self._resolve_metrics(
            latest_metrics=latest_metrics,
            started_at=execution_context.started_at,
            finished_at=completion_timestamp,
        )
        final_report = self._build_execution_report(
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
            started_at=execution_context.started_at,
            finished_at=completion_timestamp,
            metrics=final_metrics,
            completed=True,
        )
        final_context = self._advance_context(
            current_context,
            current_step=current_context.current_step,
            current_state=self.state_machine.current_state,
            current_timestamp=completion_timestamp,
            metrics=final_metrics,
        )
        self._sync_tracker(
            context=final_context,
            current_timestamp=completion_timestamp,
            metrics=final_metrics,
            report=final_report,
        )
        return self._build_result(
            success=True,
            report=final_report,
            metrics=final_metrics,
            started_at=execution_context.started_at,
            completed_at=completion_timestamp,
            errors=(),
        )

    def shutdown(self) -> None:
        """Release runner resources after pipeline execution completes."""

        return None

    def _build_initial_snapshot(self, started_at: datetime) -> ProgressSnapshot:
        """Create the initial progress snapshot for a run."""

        return ProgressSnapshot(
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
        )

    def _advance_context(
        self,
        context: ExecutionContext,
        *,
        current_step: str | None,
        current_state: MigrationState,
        current_timestamp: datetime,
        metrics: MigrationMetrics | None,
    ) -> ExecutionContext:
        """Create a new execution context for the current runner state."""

        return replace(
            context,
            current_step=current_step,
            metrics=metrics,
            progress_tracker=self.progress_tracker or context.progress_tracker,
            state=current_state,
            current_timestamp=current_timestamp,
        )

    def _sync_tracker(
        self,
        *,
        context: ExecutionContext,
        current_timestamp: datetime,
        metrics: MigrationMetrics,
        report: ExecutionReport,
    ) -> None:
        """Synchronize the tracker with the runner's latest orchestration state."""

        if self.progress_tracker is None:
            return

        current_snapshot = replace(
            self.progress_tracker.current_snapshot,
            total_items=metrics.total_items,
            processed_items=metrics.processed_items,
            successful_items=metrics.successful_items,
            failed_items=metrics.failed_items,
            skipped_items=metrics.skipped_items,
            last_updated=current_timestamp,
        )
        execution_context = replace(
            context,
            metrics=metrics,
            progress_tracker=self.progress_tracker,
            current_timestamp=current_timestamp,
        )
        self.progress_tracker.update_snapshot(current_snapshot)
        self.progress_tracker.update_execution_context(execution_context)
        self.progress_tracker.update_metrics(metrics)
        self.progress_tracker.update_execution_report(report)
        self.progress_tracker.update_migration_state(self.state_machine.current_state)
        self.execution_context = execution_context
        self.execution_report = report
        self.metrics = metrics

    def _resolve_metrics(
        self,
        *,
        latest_metrics: MigrationMetrics | None,
        started_at: datetime,
        finished_at: datetime,
    ) -> MigrationMetrics:
        """Resolve the metrics object for the current orchestration state."""

        duration_seconds = max((finished_at - started_at).total_seconds(), 0.0)
        if latest_metrics is not None:
            throughput = (
                latest_metrics.processed_items / duration_seconds if duration_seconds > 0.0 else 0.0
            )
            return replace(
                latest_metrics,
                duration_seconds=duration_seconds,
                throughput_items_per_second=throughput,
                started_at=started_at,
                finished_at=finished_at,
            )

        return MigrationMetrics(
            duration_seconds=duration_seconds,
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
            total_bytes=0,
            started_at=started_at,
            finished_at=finished_at,
        )

    def _build_execution_report(
        self,
        *,
        successful_steps: int,
        failed_steps: int,
        skipped_steps: int,
        started_at: datetime,
        finished_at: datetime,
        metrics: MigrationMetrics,
        completed: bool,
    ) -> ExecutionReport:
        """Build an execution report for the current orchestration state."""

        duration = max((finished_at - started_at).total_seconds(), 0.0)
        return ExecutionReport(
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
            duration_seconds=duration,
            completed=completed,
            metrics=metrics,
        )

    def _build_result(
        self,
        *,
        success: bool,
        report: ExecutionReport,
        metrics: MigrationMetrics,
        started_at: datetime,
        completed_at: datetime,
        errors: tuple[str, ...],
    ) -> ExecutionResult:
        """Build the immutable execution result for the runner run."""

        duration = completed_at - started_at
        self.execution_result = ExecutionResult(
            success=success,
            execution_report=report,
            metrics=metrics,
            completed_at=completed_at,
            duration=duration,
            warnings=(),
            errors=errors,
        )
        return self.execution_result

    def _rollback_steps(
        self,
        *,
        completed_steps: Sequence[PipelineStep],
        current_step: PipelineStep,
        context: ExecutionContext,
    ) -> None:
        """Rollback the current step and any previously completed steps."""

        for step in [current_step, *reversed(completed_steps)]:
            try:
                step.rollback(context)
            except Exception:
                continue

    def _step_state(self, step: PipelineStep) -> MigrationState | None:
        """Map a pipeline step to a migration lifecycle state."""

        state_name = step.__class__.__name__
        return {
            "DiscoverArchivesStep": MigrationState.DISCOVERING,
            "ExtractItemsStep": MigrationState.EXTRACTING,
            "TransformItemsStep": MigrationState.TRANSFORMING,
            "UploadItemsStep": MigrationState.UPLOADING,
            "VerifyItemsStep": MigrationState.VERIFYING,
            "FinalizeMigrationStep": MigrationState.FINALIZING,
        }.get(state_name)

    def _is_successful(self, report: ExecutionReport) -> bool:
        """Determine whether a step report represents a successful step."""

        return report.completed and report.failed_steps == 0

    def _current_timestamp(self) -> datetime:
        """Return the current UTC timestamp for orchestration bookkeeping."""

        return datetime.now(tz=UTC)


__all__: list[str] = ["PipelineRunner"]
