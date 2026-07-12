"""Regression tests for the migration orchestrator façade.

This module verifies that the public orchestrator remains a thin delegation
layer over the concrete pipeline runner while honoring constructor injection
for pipeline composition.
"""

from __future__ import annotations

from datetime import UTC, datetime

from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ProgressSnapshot
from migration_engine.execution_result import ExecutionResult
from migration_engine.metrics import MigrationMetrics
from migration_engine.orchestrator import MigrationOrchestrator
from migration_engine.pipeline import MigrationPipeline
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.runner import PipelineRunner, StepRegistry
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import DiscoverArchivesStep


def _build_initial_context() -> MigrationStepContext:
    """Create a minimal initial migration step context for delegation tests."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
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
        migration_state=MigrationState.CREATED,
    )
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step=None,
        metrics=MigrationMetrics(
            duration_seconds=0.0,
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
            finished_at=started_at,
        ),
        progress_tracker=progress_tracker,
        state=MigrationState.CREATED,
        current_timestamp=started_at,
    )
    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=progress_tracker,
        state_machine=MigrationStateMachine(current_state=MigrationState.CREATED),
    )


class _RecordingRunner(PipelineRunner):
    """Record runner invocations without executing a workflow."""

    def __init__(self) -> None:
        """Create a runner stub for orchestrator delegation tests."""

        super().__init__(())
        self.run_calls = 0
        self.result = ExecutionResult(success=True, warnings=("delegated",))

    def run(self) -> ExecutionResult:
        """Record the run call and return the configured execution result."""

        self.run_calls += 1
        return self.result


def test_migration_orchestrator_delegates_to_runner() -> None:
    """The orchestrator should delegate execution to the injected runner."""

    runner = _RecordingRunner()
    step_registry = StepRegistry((DiscoverArchivesStep(),))
    pipeline = MigrationPipeline(steps=(DiscoverArchivesStep(),))
    initial_context = _build_initial_context()

    orchestrator = MigrationOrchestrator(
        runner=runner,
        step_registry=step_registry,
        initial_context=initial_context,
        pipeline=pipeline,
    )
    result = orchestrator.run()

    assert result is runner.result
    assert runner.run_calls == 1
    assert runner.step_registry is step_registry
    assert runner.pipeline is pipeline
    assert runner.initial_context is initial_context
