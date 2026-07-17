"""Regression tests for Sprint 8.2 SIS rehydration and cleanup alignment.

This module verifies that the repository keeps a single canonical
orchestration implementation, that the dry-run application use case delegates
to the existing pipeline while forcing analysis-only execution, and that the
rehydration package exposes the real target-neutral SIS APIs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from application.orchestrators import (
    MigrationOrchestrator as ApplicationMigrationOrchestrator,
)
from application.use_cases import (
    DryRunMigrationUseCase as ExportedDryRunMigrationUseCase,
)
from application.use_cases.dry_run import DryRunMigrationUseCase
from migration_engine import rehydration
from migration_engine.checkpoint import CheckpointSnapshot
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ProgressSnapshot
from migration_engine.execution_result import ExecutionResult
from migration_engine.metrics import MigrationMetrics
from migration_engine.orchestrator import MigrationOrchestrator
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.rehydration import (
    RehydratedContent as ExportedRehydratedContent,
)
from migration_engine.rehydration import (
    SisRehydrator as ExportedSisRehydrator,
)
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext


def _build_initial_context() -> MigrationStepContext:
    """Create a deterministic initial context for cleanup tests."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    configuration = MigrationConfiguration(
        dry_run=False,
        archive_names=("Archive One",),
        folder_paths=("/Inbox",),
    )
    metrics = MigrationMetrics(
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
        migration_state=MigrationState.CREATED,
    )
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=configuration,
        started_at=started_at,
        current_step=None,
        metrics=metrics,
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
    """Record dry-run orchestration calls without executing a workflow."""

    def __init__(self) -> None:
        """Create a runner stub for orchestration cleanup tests."""

        super().__init__(())
        self.run_calls = 0
        self.recorded_context: MigrationStepContext | None = None
        self.result = ExecutionResult(success=True, warnings=("delegated",))

    def run(
        self,
        *,
        resume_checkpoint: CheckpointSnapshot | None = None,
    ) -> ExecutionResult:
        """Record the injected initial context and return the configured result."""

        self.run_calls += 1
        self.recorded_context = self.initial_context
        return self.result


def test_application_orchestrator_import_is_the_canonical_implementation() -> None:
    """The application import path should re-export the canonical orchestrator."""

    assert ApplicationMigrationOrchestrator is MigrationOrchestrator


def test_dry_run_use_case_forces_dry_run_and_delegates_to_pipeline() -> None:
    """The dry-run use case should force dry-run mode and delegate execution."""

    runner = _RecordingRunner()
    orchestrator = MigrationOrchestrator(runner=runner)
    use_case = DryRunMigrationUseCase(migration_orchestrator=orchestrator)
    initial_context = _build_initial_context()

    result = use_case.execute(initial_context=initial_context)

    assert result is runner.result
    assert runner.run_calls == 1
    assert runner.recorded_context is not None
    assert runner.recorded_context.execution_context.configuration.dry_run is True
    assert runner.recorded_context.execution_context.configuration.archive_names == ("Archive One",)
    assert runner.recorded_context.execution_context.configuration.folder_paths == ("/Inbox",)
    assert runner.initial_context is None
    assert result.warnings == ("delegated",)
    assert ExportedDryRunMigrationUseCase is DryRunMigrationUseCase


def test_rehydration_package_exposes_no_placeholder_apis() -> None:
    """The rehydration package should expose the concrete SIS APIs."""

    assert rehydration.__all__ == ["RehydratedContent", "SisRehydrator"]
    assert rehydration.RehydratedContent is ExportedRehydratedContent
    assert rehydration.SisRehydrator is ExportedSisRehydrator
