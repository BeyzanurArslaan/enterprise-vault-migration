"""Regression tests for the migration pipeline runner."""

from __future__ import annotations

from datetime import UTC, datetime

from migration_engine.contracts import ExecutionContext, ExecutionReport, PipelineStep
from migration_engine.metrics import MigrationMetrics
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState


def _build_metrics(
    *,
    total_items: int,
    processed_items: int,
    successful_items: int,
    failed_items: int,
    skipped_items: int,
) -> MigrationMetrics:
    """Create a sample metrics object for runner tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=1.0,
        throughput_items_per_second=1.0,
        average_item_size=1024,
        processed_bytes=2048,
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
        total_bytes=4096,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_report(
    *,
    successful_steps: int,
    failed_steps: int,
    skipped_steps: int,
    total_items: int,
    processed_items: int,
    successful_items: int,
    failed_items: int,
    skipped_items: int,
) -> ExecutionReport:
    """Create a sample execution report for runner tests."""

    return ExecutionReport(
        successful_steps=successful_steps,
        failed_steps=failed_steps,
        skipped_steps=skipped_steps,
        duration_seconds=1.0,
        completed=True,
        metrics=_build_metrics(
            total_items=total_items,
            processed_items=processed_items,
            successful_items=successful_items,
            failed_items=failed_items,
            skipped_items=skipped_items,
        ),
    )


class _RecordingStep(PipelineStep):
    """Record pipeline lifecycle calls for orchestration assertions."""

    def __init__(self, report: ExecutionReport) -> None:
        self._report = report
        self.calls: list[str] = []

    def prepare(self, context: ExecutionContext) -> None:
        state = context.state
        assert state is not None
        self.calls.append(f"prepare:{context.current_step}:{state.value}")

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        state = context.state
        assert state is not None
        self.calls.append(f"execute:{context.current_step}:{state.value}")
        return self._report

    def finalize(self, context: ExecutionContext) -> None:
        state = context.state
        assert state is not None
        self.calls.append(f"finalize:{context.current_step}:{state.value}")

    def rollback(self, context: ExecutionContext) -> None:
        state = context.state
        assert state is not None
        self.calls.append(f"rollback:{context.current_step}:{state.value}")


class DiscoverArchivesStep(_RecordingStep):
    """Concrete recording step mapped to archive discovery state."""


class FinalizeMigrationStep(_RecordingStep):
    """Concrete recording step mapped to migration finalization state."""


class UploadItemsStep(_RecordingStep):
    """Concrete recording step that can raise during execution."""

    def __init__(self, report: ExecutionReport, *, fail_on_execute: bool = False) -> None:
        super().__init__(report)
        self._fail_on_execute = fail_on_execute

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        state = context.state
        assert state is not None
        self.calls.append(f"execute:{context.current_step}:{state.value}")
        if self._fail_on_execute:
            raise RuntimeError("upload failed")

        return self._report


def test_pipeline_runner_initializes_and_completes_execution_flow() -> None:
    """The runner should initialize, run steps, and finish successfully."""

    first_step = DiscoverArchivesStep(
        _build_report(
            successful_steps=1,
            failed_steps=0,
            skipped_steps=0,
            total_items=1,
            processed_items=1,
            successful_items=1,
            failed_items=0,
            skipped_items=0,
        )
    )
    second_step = FinalizeMigrationStep(
        _build_report(
            successful_steps=1,
            failed_steps=0,
            skipped_steps=0,
            total_items=2,
            processed_items=2,
            successful_items=2,
            failed_items=0,
            skipped_items=0,
        )
    )

    runner = PipelineRunner([first_step, second_step])
    initialized_context = runner.initialize()

    assert initialized_context.current_step is None
    assert initialized_context.state == MigrationState.INITIALIZING
    assert runner.state_machine.current_state == MigrationState.INITIALIZING
    assert runner.progress_tracker is not None
    assert runner.progress_tracker.current_migration_state == MigrationState.INITIALIZING

    result = runner.run()

    assert result.success is True
    assert result.execution_report is not None
    assert result.execution_report.completed is True
    assert result.execution_report.successful_steps == 2
    assert result.execution_report.failed_steps == 0
    assert result.execution_report.metrics is not None
    assert result.execution_report.metrics.total_items == 2
    assert result.execution_report.metrics.processed_items == 2
    assert result.metrics == result.execution_report.metrics
    assert result.completed_at is not None
    assert result.duration is not None
    assert result.duration.total_seconds() >= 0.0
    assert runner.execution_result == result
    assert runner.execution_report == result.execution_report
    assert runner.execution_context is not None
    assert runner.execution_context.state is not None
    assert runner.execution_context.state.value == MigrationState.COMPLETED.value
    assert runner.execution_context.current_step == "FinalizeMigrationStep"
    assert runner.state_machine.current_state.value == MigrationState.COMPLETED.value
    assert runner.progress_tracker is not None
    assert runner.progress_tracker.current_migration_state is not None
    assert runner.progress_tracker.current_migration_state.value == MigrationState.COMPLETED.value
    assert runner.progress_tracker.current_snapshot.processed_items == 2
    assert runner.progress_tracker.current_snapshot.successful_items == 2
    assert runner.progress_tracker.current_execution_report == result.execution_report
    assert first_step.calls == [
        "prepare:DiscoverArchivesStep:discovering",
        "execute:DiscoverArchivesStep:discovering",
        "finalize:DiscoverArchivesStep:discovering",
    ]
    assert second_step.calls == [
        "prepare:FinalizeMigrationStep:finalizing",
        "execute:FinalizeMigrationStep:finalizing",
        "finalize:FinalizeMigrationStep:finalizing",
    ]


def test_pipeline_runner_rolls_back_and_marks_failure() -> None:
    """The runner should roll back steps and fail the run on execution errors."""

    first_step = DiscoverArchivesStep(
        _build_report(
            successful_steps=1,
            failed_steps=0,
            skipped_steps=0,
            total_items=1,
            processed_items=1,
            successful_items=1,
            failed_items=0,
            skipped_items=0,
        )
    )
    second_step = UploadItemsStep(
        _build_report(
            successful_steps=0,
            failed_steps=0,
            skipped_steps=0,
            total_items=1,
            processed_items=1,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
        ),
        fail_on_execute=True,
    )

    runner = PipelineRunner([first_step, second_step])
    result = runner.run()

    assert result.success is False
    assert result.execution_report is not None
    assert result.execution_report.completed is False
    assert result.execution_report.successful_steps == 1
    assert result.execution_report.failed_steps == 0
    assert result.execution_report.metrics is not None
    assert result.execution_report.metrics.total_items == 1
    assert result.execution_report.metrics.processed_items == 1
    assert runner.execution_result == result
    assert runner.execution_context is not None
    assert runner.execution_context.state is not None
    assert runner.execution_context.state.value == MigrationState.FAILED.value
    assert runner.state_machine.current_state.value == MigrationState.FAILED.value
    assert runner.progress_tracker is not None
    assert runner.progress_tracker.current_migration_state is not None
    assert runner.progress_tracker.current_migration_state.value == MigrationState.FAILED.value
    assert runner.progress_tracker.current_execution_report == result.execution_report
    assert first_step.calls == [
        "prepare:DiscoverArchivesStep:discovering",
        "execute:DiscoverArchivesStep:discovering",
        "finalize:DiscoverArchivesStep:discovering",
        "rollback:UploadItemsStep:failed",
    ]
    assert second_step.calls == [
        "prepare:UploadItemsStep:uploading",
        "execute:UploadItemsStep:uploading",
        "rollback:UploadItemsStep:failed",
    ]
