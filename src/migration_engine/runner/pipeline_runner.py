"""Pipeline runner module for the migration engine execution layer.

This module defines the runner that coordinates registered pipeline steps with
execution state, progress tracking, metrics, checkpoint persistence, and final
reporting.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from application.services import CheckpointService
from domain.entities import RetryRecord
from domain.value_objects.identifiers import RetryRecordId
from ports.identifier_generator_port import IdentifierGeneratorPort
from ports.retry_repository_port import RetryRepositoryPort

from ..checkpoint import CheckpointSnapshot
from ..configuration import MigrationConfiguration
from ..context import MigrationContext
from ..contracts import ExecutionContext, ExecutionReport, PipelineStep, ProgressSnapshot
from ..execution_result import ExecutionResult
from ..metrics import MigrationMetrics
from ..pipeline import MigrationPipeline
from ..progress_tracker import ProgressTracker
from ..retry import RetryDecision, RetryPolicy
from ..state_machine import MigrationState, MigrationStateMachine
from ..step_context import MigrationStepContext
from ..steps import (
    DiscoverArchivesStep,
    ExtractItemsStep,
    FinalizeMigrationStep,
    TransformItemsStep,
    UploadItemsStep,
    VerifyItemsStep,
)
from .step_registry import StepRegistry


class PipelineRunner:
    """Coordinate pipeline steps, execution state, checkpoints, and outcomes."""

    def __init__(
        self,
        steps: Sequence[PipelineStep] = (),
        *,
        pipeline: MigrationPipeline | None = None,
        step_registry: StepRegistry | None = None,
        initial_context: MigrationStepContext | None = None,
        context: MigrationContext | None = None,
        checkpoint_service: CheckpointService | None = None,
        identifier_generator: IdentifierGeneratorPort | None = None,
        retry_policy: RetryPolicy | None = None,
        retry_repository: RetryRepositoryPort | None = None,
        retry_classifier: Callable[[Exception], bool] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        """Create a runner configured with ordered pipeline steps."""

        if step_registry is not None:
            self.step_registry = step_registry
        elif pipeline is not None:
            self.step_registry = StepRegistry(pipeline.steps)
        else:
            self.step_registry = StepRegistry(steps)
        self.steps: tuple[PipelineStep, ...] = self.step_registry.resolve()
        self.pipeline = pipeline or MigrationPipeline(steps=self.steps)
        self.context = context
        self.initial_context = initial_context
        self.state_machine = MigrationStateMachine(current_state=MigrationState.CREATED)
        self.progress_tracker: ProgressTracker | None = None
        self.execution_context: ExecutionContext | None = None
        self.execution_report: ExecutionReport | None = None
        self.execution_result: ExecutionResult | None = None
        self.metrics: MigrationMetrics | None = None
        self.current_step_context: MigrationStepContext | None = initial_context
        self.checkpoint_service = checkpoint_service
        self.identifier_generator = identifier_generator
        self.retry_policy = retry_policy
        self.retry_repository = retry_repository
        self.retry_classifier = retry_classifier
        self.sleeper = sleeper

    def initialize(self) -> ExecutionContext:
        """Prepare the runner before pipeline execution begins."""

        if self.execution_context is not None:
            return self.execution_context

        self.steps = self.step_registry.resolve()
        execution_context, progress_tracker, step_context = self._build_initial_runtime()
        self.progress_tracker = progress_tracker
        self.execution_context = execution_context
        self.current_step_context = step_context
        return execution_context

    def run(
        self,
        *,
        resume_checkpoint: CheckpointSnapshot | None = None,
    ) -> ExecutionResult:
        """Execute the configured pipeline steps in order."""

        self.steps = self.step_registry.resolve()
        if resume_checkpoint is None:
            execution_context = self.initialize()
            successful_steps = 0
            failed_steps = 0
            skipped_steps = 0
            latest_metrics = self.metrics
            current_context = execution_context
            current_step_context = self._build_current_step_context(execution_context)
            start_index = 0
            errors: list[str] = []
        else:
            (
                execution_context,
                current_step_context,
                successful_steps,
                failed_steps,
                skipped_steps,
                latest_metrics,
                errors,
                start_index,
            ) = self._build_resume_runtime(resume_checkpoint)
            current_context = execution_context

        completed_steps: list[PipelineStep] = []

        for step in self.steps[start_index:]:
            step_state = self._step_state(step)
            if step_state is not None and self.state_machine.can_transition(step_state):
                self.state_machine.transition_to(step_state)

            attempt_number = 1
            while True:
                attempt_timestamp = self._current_timestamp()
                attempt_context = self._advance_context(
                    current_context,
                    current_step=step.__class__.__name__,
                    current_state=self.state_machine.current_state,
                    current_timestamp=attempt_timestamp,
                    metrics=latest_metrics,
                )
                attempt_step_context = replace(
                    current_step_context,
                    execution_context=attempt_context,
                    progress_tracker=(
                        self.progress_tracker or current_step_context.progress_tracker
                    ),
                    state_machine=self.state_machine,
                )

                try:
                    step.prepare(attempt_context)
                    step_result_context = self._execute_step(step, attempt_step_context)
                    if step_result_context is not None:
                        current_step_context = step_result_context
                        current_context = step_result_context.execution_context
                        step_report = step_result_context.execution_report
                        if step_report is None:
                            message = (
                                f"{step.__class__.__name__} did not produce an " "execution report"
                            )
                            raise RuntimeError(message)
                        latest_metrics = self._merge_retry_metrics(
                            current_metrics=(
                                step_result_context.execution_context.metrics or step_report.metrics
                            ),
                            latest_metrics=latest_metrics,
                        )
                    else:
                        step_report = step.execute(attempt_context)
                        if step_report.metrics is not None:
                            latest_metrics = self._merge_retry_metrics(
                                current_metrics=step_report.metrics,
                                latest_metrics=latest_metrics,
                            )

                    success_timestamp = self._current_timestamp()
                    current_context = self._advance_context(
                        current_context,
                        current_step=step.__class__.__name__,
                        current_state=self.state_machine.current_state,
                        current_timestamp=success_timestamp,
                        metrics=latest_metrics,
                    )
                    resolved_metrics = self._resolve_metrics(
                        latest_metrics=latest_metrics,
                        started_at=execution_context.started_at,
                        finished_at=success_timestamp,
                    )
                    step.finalize(current_context)
                    successful_steps += step_report.successful_steps
                    failed_steps += step_report.failed_steps
                    skipped_steps += step_report.skipped_steps
                    self._sync_tracker(
                        context=current_context,
                        current_timestamp=success_timestamp,
                        metrics=resolved_metrics,
                        report=step_report,
                    )

                    current_step_context = replace(
                        current_step_context,
                        execution_context=current_context,
                        progress_tracker=(
                            self.progress_tracker or current_step_context.progress_tracker
                        ),
                        state_machine=self.state_machine,
                        execution_report=step_report,
                    )
                    current_step_context = self._save_checkpoint(current_step_context)
                    self.current_step_context = current_step_context
                    completed_steps.append(step)
                    break
                except Exception as exc:
                    retry_decision = self._decide_retry(
                        exception=exc,
                        attempt_number=attempt_number,
                    )
                    if retry_decision is not None and retry_decision.should_retry:
                        retry_timestamp = self._current_timestamp()
                        retry_metrics = self._build_retry_metrics(
                            latest_metrics=latest_metrics,
                            started_at=execution_context.started_at,
                            finished_at=retry_timestamp,
                        )
                        retry_record = self._build_retry_record(
                            migration_id=execution_context.migration_id,
                            step_name=step.__class__.__name__,
                            attempt_number=attempt_number,
                            retry_timestamp=retry_timestamp,
                            reason=retry_decision.reason,
                        )
                        if self.retry_repository is not None:
                            self.retry_repository.save(retry_record)
                        current_context = self._sync_retry_state(
                            context=attempt_context,
                            current_timestamp=retry_timestamp,
                            metrics=retry_metrics,
                        )
                        current_step_context = replace(
                            attempt_step_context,
                            execution_context=current_context,
                            progress_tracker=(
                                self.progress_tracker or attempt_step_context.progress_tracker
                            ),
                            state_machine=self.state_machine,
                        )
                        self.current_step_context = current_step_context
                        if self.sleeper is not None:
                            self.sleeper(retry_decision.delay_seconds)
                        latest_metrics = retry_metrics
                        attempt_number += 1
                        continue

                    errors.append(str(exc))
                    failure_timestamp = self._current_timestamp()
                    failure_state = MigrationState.FAILED
                    self.state_machine.transition_to(failure_state)
                    failure_context = self._advance_context(
                        attempt_context,
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
                    self.current_step_context = replace(
                        current_step_context,
                        execution_context=failure_context,
                        progress_tracker=(
                            self.progress_tracker or current_step_context.progress_tracker
                        ),
                        state_machine=self.state_machine,
                        execution_report=failure_report,
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
        self.current_step_context = replace(
            current_step_context,
            execution_context=final_context,
            progress_tracker=(self.progress_tracker or current_step_context.progress_tracker),
            state_machine=self.state_machine,
            execution_report=final_report,
        )
        if self.current_step_context.execution_result is not None:
            self.execution_result = self.current_step_context.execution_result
            self.execution_report = final_report
            self.execution_context = final_context
            self.metrics = final_metrics
            return self.current_step_context.execution_result
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

    def _build_initial_runtime(
        self,
    ) -> tuple[ExecutionContext, ProgressTracker, MigrationStepContext]:
        """Build the initial execution and step contexts for a run."""

        if self.initial_context is not None:
            execution_context = self.initial_context.execution_context
            started_at = execution_context.started_at
            self.state_machine = MigrationStateMachine(
                current_state=execution_context.state or MigrationState.CREATED,
            )
            if self.state_machine.can_transition(MigrationState.INITIALIZING):
                self.state_machine.transition_to(MigrationState.INITIALIZING)

            progress_tracker = (
                self.initial_context.progress_tracker
                or execution_context.progress_tracker
                or ProgressTracker(
                    snapshot=self._build_initial_snapshot(started_at),
                    migration_state=self.state_machine.current_state,
                )
            )
            resolved_execution_context = replace(
                execution_context,
                current_step=None,
                metrics=self.metrics or execution_context.metrics,
                progress_tracker=progress_tracker,
                state=self.state_machine.current_state,
                current_timestamp=execution_context.current_timestamp or started_at,
            )
            step_context = replace(
                self.initial_context,
                execution_context=resolved_execution_context,
                progress_tracker=progress_tracker,
                state_machine=self.state_machine,
            )
            progress_tracker.update_execution_context(resolved_execution_context)
            progress_tracker.update_migration_state(self.state_machine.current_state)
            return resolved_execution_context, progress_tracker, step_context

        started_at = self._current_timestamp()
        self.state_machine.transition_to(MigrationState.INITIALIZING)
        progress_tracker = ProgressTracker(
            snapshot=self._build_initial_snapshot(started_at),
            migration_state=self.state_machine.current_state,
        )
        execution_context = ExecutionContext(
            migration_id=self._resolve_migration_id(),
            configuration=MigrationConfiguration(),
            started_at=started_at,
            current_step=None,
            metrics=self.metrics,
            progress_tracker=progress_tracker,
            state=self.state_machine.current_state,
            current_timestamp=started_at,
        )
        progress_tracker.update_execution_context(execution_context)
        step_context = MigrationStepContext(
            execution_context=execution_context,
            progress_tracker=progress_tracker,
            state_machine=self.state_machine,
            execution_report=None,
        )
        return execution_context, progress_tracker, step_context

    def _build_current_step_context(
        self,
        execution_context: ExecutionContext,
    ) -> MigrationStepContext:
        """Return the runtime step context used for concrete step execution."""

        if self.current_step_context is not None:
            return replace(
                self.current_step_context,
                execution_context=execution_context,
                progress_tracker=(
                    self.progress_tracker or self.current_step_context.progress_tracker
                ),
                state_machine=self.state_machine,
            )

        return MigrationStepContext(
            execution_context=execution_context,
            progress_tracker=self.progress_tracker or execution_context.progress_tracker,
            state_machine=self.state_machine,
            execution_report=self.execution_report,
        )

    def _execute_step(
        self,
        step: PipelineStep,
        context: MigrationStepContext,
    ) -> MigrationStepContext | None:
        """Execute a step using its concrete migration contract when available."""

        if type(step) is DiscoverArchivesStep:
            return step.discover(context)
        if type(step) is ExtractItemsStep:
            return step.extract(context)
        if type(step) is TransformItemsStep:
            return step.transform(context)
        if type(step) is UploadItemsStep:
            return step.upload(context)
        if type(step) is VerifyItemsStep:
            return step.verify(context)
        if type(step) is FinalizeMigrationStep:
            return step.finalize_migration(context)

        return None

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

    def _decide_retry(
        self,
        *,
        exception: Exception,
        attempt_number: int,
    ) -> RetryDecision | None:
        """Evaluate whether a failed step attempt should be retried."""

        if self.retry_policy is None or self.retry_classifier is None:
            return None

        retryable = self.retry_classifier(exception)
        return self.retry_policy.decide(
            attempt_number=attempt_number,
            retryable=retryable,
            reason=str(exception),
        )

    def _build_retry_metrics(
        self,
        *,
        latest_metrics: MigrationMetrics | None,
        started_at: datetime,
        finished_at: datetime,
    ) -> MigrationMetrics:
        """Build retry-aware metrics for a failed step attempt."""

        retry_metrics = self._resolve_metrics(
            latest_metrics=latest_metrics,
            started_at=started_at,
            finished_at=finished_at,
        )
        return replace(retry_metrics, retried_items=retry_metrics.retried_items + 1)

    def _merge_retry_metrics(
        self,
        *,
        current_metrics: MigrationMetrics | None,
        latest_metrics: MigrationMetrics | None,
    ) -> MigrationMetrics | None:
        """Preserve retry counters when a step reports fresh metrics."""

        if current_metrics is None:
            return latest_metrics

        if latest_metrics is None:
            return current_metrics

        retried_items = max(current_metrics.retried_items, latest_metrics.retried_items)
        if retried_items == current_metrics.retried_items:
            return current_metrics

        return replace(current_metrics, retried_items=retried_items)

    def _build_retry_record(
        self,
        *,
        migration_id: str,
        step_name: str,
        attempt_number: int,
        retry_timestamp: datetime,
        reason: str | None,
    ) -> RetryRecord:
        """Create a retry record for a retryable step failure."""

        if self.retry_policy is None:
            message = "Retry policy is required to build a retry record."
            raise RuntimeError(message)

        retry_record_id = RetryRecordId(
            value=uuid5(NAMESPACE_URL, f"{migration_id}:{step_name}:{attempt_number}")
        )
        return RetryRecord(
            id=retry_record_id,
            migration_item_id=None,
            retry_strategy=self.retry_policy.strategy,
            attempt_number=attempt_number,
            migration_job_id=migration_id,
            pipeline_step_name=step_name,
            retry_reason=reason,
            created_at=retry_timestamp,
            updated_at=retry_timestamp,
        )

    def _sync_retry_state(
        self,
        *,
        context: ExecutionContext,
        current_timestamp: datetime,
        metrics: MigrationMetrics,
    ) -> ExecutionContext:
        """Synchronize tracker state after a retry decision is recorded."""

        retry_context = replace(
            context,
            metrics=metrics,
            progress_tracker=self.progress_tracker or context.progress_tracker,
            current_timestamp=current_timestamp,
        )
        if self.progress_tracker is not None:
            retry_snapshot = replace(
                self.progress_tracker.current_snapshot,
                last_updated=current_timestamp,
            )
            self.progress_tracker.update_snapshot(retry_snapshot)
            self.progress_tracker.update_execution_context(retry_context)
            self.progress_tracker.update_metrics(metrics)
            self.progress_tracker.update_migration_state(self.state_machine.current_state)

        self.execution_context = retry_context
        self.metrics = metrics
        return retry_context

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

    def _current_timestamp(self) -> datetime:
        """Return the current UTC timestamp for orchestration bookkeeping."""

        return datetime.now(tz=UTC)

    def _save_checkpoint(self, context: MigrationStepContext) -> MigrationStepContext:
        """Persist the latest successful step checkpoint when enabled."""

        if self.checkpoint_service is None:
            return context

        checkpoint = self._build_checkpoint_snapshot(context)
        self.checkpoint_service.save_checkpoint(checkpoint)
        return replace(context, checkpoint=checkpoint)

    def _build_resume_runtime(
        self,
        resume_checkpoint: CheckpointSnapshot,
    ) -> tuple[
        ExecutionContext,
        MigrationStepContext,
        int,
        int,
        int,
        MigrationMetrics | None,
        list[str],
        int,
    ]:
        """Restore the runtime state and replay completed stages from a checkpoint."""

        resume_index = self._resolve_resume_index(resume_checkpoint)
        resumed_state = MigrationState(resume_checkpoint.current_state)
        started_at = resume_checkpoint.created_at
        updated_at = resume_checkpoint.updated_at
        restored_metrics = self._build_checkpoint_metrics(
            checkpoint=resume_checkpoint,
            started_at=started_at,
            finished_at=updated_at,
        )
        restored_snapshot = self._build_checkpoint_progress_snapshot(
            checkpoint=resume_checkpoint,
            started_at=started_at,
            updated_at=updated_at,
        )
        self.state_machine = MigrationStateMachine(current_state=resumed_state)
        self.progress_tracker = ProgressTracker(
            snapshot=restored_snapshot,
            metrics=restored_metrics,
            migration_state=resumed_state,
        )
        execution_context = ExecutionContext(
            migration_id=resume_checkpoint.migration_job_id,
            configuration=self._resolve_resume_configuration(resume_checkpoint),
            started_at=started_at,
            current_step=resume_checkpoint.last_completed_step,
            metrics=restored_metrics,
            progress_tracker=self.progress_tracker,
            state=resumed_state,
            current_timestamp=updated_at,
        )
        self.progress_tracker.update_execution_context(execution_context)
        self.progress_tracker.update_metrics(restored_metrics)
        self.progress_tracker.update_migration_state(resumed_state)
        current_context = execution_context
        current_step_context = MigrationStepContext(
            execution_context=execution_context,
            progress_tracker=self.progress_tracker,
            state_machine=self.state_machine,
            execution_report=None,
            checkpoint=resume_checkpoint,
        )

        successful_steps = 0
        failed_steps = 0
        skipped_steps = 0
        latest_metrics: MigrationMetrics | None = restored_metrics
        errors: list[str] = []

        for step in self.steps[:resume_index]:
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
            current_step_context = replace(
                current_step_context,
                execution_context=current_context,
                progress_tracker=self.progress_tracker or current_step_context.progress_tracker,
                state_machine=self.state_machine,
            )

            step.prepare(current_context)
            step_result_context: MigrationStepContext | None
            if type(step) is UploadItemsStep:
                step_result_context = step.reconstruct_upload(current_step_context)
            else:
                step_result_context = self._execute_step(step, current_step_context)
                if step_result_context is None:
                    step_report = step.execute(current_context)
                    if step_report.metrics is not None:
                        latest_metrics = self._merge_retry_metrics(
                            current_metrics=step_report.metrics,
                            latest_metrics=latest_metrics,
                        )
                    successful_steps += step_report.successful_steps
                    failed_steps += step_report.failed_steps
                    skipped_steps += step_report.skipped_steps
                    step_timestamp = self._current_timestamp()
                    current_context = self._advance_context(
                        current_context,
                        current_step=step.__class__.__name__,
                        current_state=self.state_machine.current_state,
                        current_timestamp=step_timestamp,
                        metrics=latest_metrics,
                    )
                    resolved_metrics = self._resolve_metrics(
                        latest_metrics=latest_metrics,
                        started_at=execution_context.started_at,
                        finished_at=step_timestamp,
                    )
                    self._sync_tracker(
                        context=current_context,
                        current_timestamp=step_timestamp,
                        metrics=resolved_metrics,
                        report=step_report,
                    )
                    current_step_context = replace(
                        current_step_context,
                        execution_context=current_context,
                        progress_tracker=(
                            self.progress_tracker or current_step_context.progress_tracker
                        ),
                        state_machine=self.state_machine,
                        execution_report=step_report,
                    )
                    step.finalize(current_context)
                    continue

            if step_result_context is None:
                message = f"{step.__class__.__name__} did not produce a reconstructed context"
                raise RuntimeError(message)

            current_step_context = step_result_context
            current_context = step_result_context.execution_context
            reconstructed_report: ExecutionReport | None = step_result_context.execution_report
            if reconstructed_report is None:
                message = f"{step.__class__.__name__} did not produce an execution report"
                raise RuntimeError(message)

            latest_metrics = self._merge_retry_metrics(
                current_metrics=(
                    step_result_context.execution_context.metrics or reconstructed_report.metrics
                ),
                latest_metrics=latest_metrics,
            )
            successful_steps += reconstructed_report.successful_steps
            failed_steps += reconstructed_report.failed_steps
            skipped_steps += reconstructed_report.skipped_steps

            step_timestamp = self._current_timestamp()
            current_context = self._advance_context(
                current_context,
                current_step=step.__class__.__name__,
                current_state=self.state_machine.current_state,
                current_timestamp=step_timestamp,
                metrics=latest_metrics,
            )
            resolved_metrics = self._resolve_metrics(
                latest_metrics=latest_metrics,
                started_at=execution_context.started_at,
                finished_at=step_timestamp,
            )
            self._sync_tracker(
                context=current_context,
                current_timestamp=step_timestamp,
                metrics=resolved_metrics,
                report=reconstructed_report,
            )
            current_step_context = replace(
                current_step_context,
                execution_context=current_context,
                progress_tracker=self.progress_tracker or current_step_context.progress_tracker,
                state_machine=self.state_machine,
                execution_report=reconstructed_report,
            )
            step.finalize(current_context)

        self.current_step_context = current_step_context
        self.execution_context = current_context
        self.execution_report = current_step_context.execution_report
        self.metrics = latest_metrics

        return (
            current_context,
            current_step_context,
            successful_steps,
            failed_steps,
            skipped_steps,
            latest_metrics,
            errors,
            resume_index,
        )

    def _build_checkpoint_metrics(
        self,
        *,
        checkpoint: CheckpointSnapshot,
        started_at: datetime,
        finished_at: datetime,
    ) -> MigrationMetrics:
        """Build metrics from a checkpoint snapshot for resume bookkeeping."""

        duration_seconds = max((finished_at - started_at).total_seconds(), 0.0)
        throughput = (
            checkpoint.processed_items / duration_seconds if duration_seconds > 0.0 else 0.0
        )
        return MigrationMetrics(
            duration_seconds=duration_seconds,
            throughput_items_per_second=throughput,
            average_item_size=0,
            processed_bytes=0,
            estimated_remaining_seconds=None,
            peak_memory_usage_mb=None,
            total_items=checkpoint.processed_items,
            processed_items=checkpoint.processed_items,
            successful_items=checkpoint.successful_items,
            failed_items=checkpoint.failed_items,
            skipped_items=checkpoint.skipped_items,
            retried_items=0,
            uploaded_items=checkpoint.uploaded_items,
            verification_failures=checkpoint.verification_failures,
            dry_run_items=checkpoint.dry_run_items,
            total_bytes=0,
            started_at=started_at,
            finished_at=finished_at,
        )

    def _build_checkpoint_progress_snapshot(
        self,
        *,
        checkpoint: CheckpointSnapshot,
        started_at: datetime,
        updated_at: datetime,
    ) -> ProgressSnapshot:
        """Build a progress snapshot from checkpoint continuation data."""

        return ProgressSnapshot(
            total_items=checkpoint.processed_items,
            processed_items=checkpoint.processed_items,
            successful_items=checkpoint.successful_items,
            failed_items=checkpoint.failed_items,
            skipped_items=checkpoint.skipped_items,
            current_archive=None,
            current_mailbox=None,
            current_item=checkpoint.last_processed_item_id,
            started_at=started_at,
            last_updated=updated_at,
        )

    def _resolve_resume_index(self, resume_checkpoint: CheckpointSnapshot) -> int:
        """Resolve the next pipeline step index for a checkpoint resume."""

        if resume_checkpoint.last_completed_step is None:
            return 0

        resume_index = self.step_registry.index_of(resume_checkpoint.last_completed_step)
        if resume_index is None:
            message = (
                "Cannot resume migration because the checkpoint completed step "
                f"{resume_checkpoint.last_completed_step!r} is not registered."
            )
            raise ValueError(message)

        if resume_index >= len(self.steps):
            message = "Cannot resume migration because the checkpoint is already final."
            raise ValueError(message)

        return resume_index + 1

    def _build_checkpoint_snapshot(self, context: MigrationStepContext) -> CheckpointSnapshot:
        """Create a checkpoint snapshot from the latest orchestration state."""

        execution_context = context.execution_context
        current_timestamp = execution_context.current_timestamp or execution_context.started_at
        metrics = execution_context.metrics or (
            context.progress_tracker.current_metrics
            if context.progress_tracker is not None
            else None
        )
        if metrics is None:
            metrics = self._resolve_metrics(
                latest_metrics=None,
                started_at=execution_context.started_at,
                finished_at=current_timestamp,
            )

        return CheckpointSnapshot(
            checkpoint_id=self._build_checkpoint_id(
                migration_id=execution_context.migration_id,
                completed_step=execution_context.current_step,
            ),
            migration_job_id=execution_context.migration_id,
            last_completed_step=execution_context.current_step,
            last_processed_item_id=self._resolve_last_processed_item_id(context),
            processed_items=metrics.processed_items,
            successful_items=metrics.successful_items,
            failed_items=metrics.failed_items,
            skipped_items=metrics.skipped_items,
            dry_run_items=metrics.dry_run_items,
            uploaded_items=metrics.uploaded_items,
            verification_failures=metrics.verification_failures,
            current_state=(
                execution_context.state.value
                if execution_context.state is not None
                else self.state_machine.current_state.value
            ),
            created_at=execution_context.started_at,
            updated_at=current_timestamp,
            dry_run=execution_context.configuration.dry_run,
            version=1,
        )

    def _resolve_last_processed_item_id(self, context: MigrationStepContext) -> str | None:
        """Return the most recent item identifier that can be checkpointed."""

        if context.verification_result is not None:
            if context.upload_result is not None and context.upload_result.uploaded_documents:
                return context.upload_result.uploaded_documents[-1].source_identifier
            if context.upload_result is not None and context.upload_result.item_results:
                return str(context.upload_result.item_results[-1].item_id.value)

        if context.upload_result is not None and context.upload_result.item_results:
            return str(context.upload_result.item_results[-1].item_id.value)

        if (
            context.transformation_result is not None
            and context.transformation_result.transformed_documents
        ):
            return context.transformation_result.transformed_documents[-1].source_identifier

        if context.extraction_result is not None and context.extraction_result.extracted_mail_items:
            return context.extraction_result.extracted_mail_items[-1].internet_message_id

        return None

    def _build_checkpoint_id(self, *, migration_id: str, completed_step: str | None) -> str:
        """Return a deterministic checkpoint identifier for the completed step."""

        resolved_step = completed_step or "unknown-step"
        return f"{migration_id}:{resolved_step}"

    def _resolve_migration_id(self) -> str:
        """Return the migration identifier for a new execution."""

        if self.identifier_generator is not None:
            return self.identifier_generator.next_job_id()

        return f"migration-{uuid4().hex}"

    def _resolve_resume_configuration(
        self,
        resume_checkpoint: CheckpointSnapshot,
    ) -> MigrationConfiguration:
        """Return the configuration used when resuming from a checkpoint."""

        if self.initial_context is not None:
            configuration = self.initial_context.execution_context.configuration
            if configuration.dry_run or resume_checkpoint.dry_run:
                return replace(configuration, dry_run=True)

            return configuration

        return MigrationConfiguration(dry_run=resume_checkpoint.dry_run)


__all__: list[str] = ["PipelineRunner"]
