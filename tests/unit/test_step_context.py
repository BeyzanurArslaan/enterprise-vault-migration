"""Regression tests for the migration step context contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from migration_engine import MigrationStepContext
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState, MigrationStateMachine


def _build_snapshot() -> ProgressSnapshot:
    """Create a sample progress snapshot for step context tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=4,
        processed_items=2,
        successful_items=1,
        failed_items=1,
        skipped_items=0,
        current_archive="archive-1",
        current_mailbox="mailbox-1",
        current_item="item-1",
        started_at=timestamp,
        last_updated=timestamp,
    )


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for step context tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=21.0,
        throughput_items_per_second=1.0,
        average_item_size=1024,
        processed_bytes=2048,
        estimated_remaining_seconds=4.0,
        peak_memory_usage_mb=128.0,
        total_items=4,
        processed_items=2,
        successful_items=1,
        failed_items=1,
        skipped_items=0,
        retried_items=0,
        uploaded_items=1,
        verification_failures=1,
        total_bytes=4096,
        started_at=timestamp,
        finished_at=None,
    )


def _build_execution_context(
    *,
    configuration: MigrationConfiguration,
    metrics: MigrationMetrics,
    tracker: ProgressTracker,
    timestamp: datetime,
) -> ExecutionContext:
    """Create a sample execution context for step context tests."""

    return ExecutionContext(
        migration_id="migration-1",
        configuration=configuration,
        started_at=timestamp,
        current_step="discover",
        metrics=metrics,
        progress_tracker=tracker,
        state=MigrationState.DISCOVERING,
        current_timestamp=timestamp,
    )


def _build_execution_report(*, metrics: MigrationMetrics) -> ExecutionReport:
    """Create a sample execution report for step context tests."""

    return ExecutionReport(
        successful_steps=2,
        failed_steps=0,
        skipped_steps=0,
        duration_seconds=21.0,
        completed=True,
        metrics=metrics,
    )


def test_migration_step_context_aggregates_engine_contracts() -> None:
    """The step context should carry existing orchestration contracts."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    configuration = MigrationConfiguration()
    metrics = _build_metrics()
    snapshot = _build_snapshot()
    tracker = ProgressTracker(snapshot=snapshot, metrics=metrics)
    execution_context = _build_execution_context(
        configuration=configuration,
        metrics=metrics,
        tracker=tracker,
        timestamp=timestamp,
    )
    state_machine = MigrationStateMachine(current_state=MigrationState.DISCOVERING)
    report = _build_execution_report(metrics=metrics)

    step_context = MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=tracker,
        state_machine=state_machine,
        execution_report=report,
    )

    assert step_context.execution_context is execution_context
    assert step_context.execution_context.configuration is configuration
    assert step_context.execution_context.metrics == metrics
    assert step_context.execution_context.progress_tracker is tracker
    assert step_context.progress_tracker is tracker
    assert step_context.state_machine is state_machine
    assert step_context.execution_report is report
    assert step_context.discovery_result is None
    assert step_context.vault_stores is None
    assert step_context.extraction_result is None
    assert step_context.transformation_result is None
    assert step_context.upload_result is None
    assert step_context.verification_result is None

    with pytest.raises(FrozenInstanceError):
        type(step_context).__setattr__(step_context, "execution_context", execution_context)
