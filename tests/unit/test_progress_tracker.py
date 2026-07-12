"""Regression tests for the migration progress tracker."""

from __future__ import annotations

from datetime import UTC, datetime

from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState


def _build_snapshot(
    *,
    processed_items: int,
    successful_items: int,
    failed_items: int,
) -> ProgressSnapshot:
    """Create a sample progress snapshot for tracker tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=10,
        processed_items=processed_items,
        successful_items=successful_items,
        failed_items=failed_items,
        skipped_items=0,
        current_archive="archive-1" if processed_items > 0 else None,
        current_mailbox="mailbox-1" if processed_items > 0 else None,
        current_item="item-1" if processed_items > 0 else None,
        started_at=timestamp,
        last_updated=timestamp,
    )


def _build_execution_context() -> ExecutionContext:
    """Create a sample execution context for tracker tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=timestamp,
        current_step="discover",
    )


def _build_execution_report(*, metrics: MigrationMetrics | None = None) -> ExecutionReport:
    """Create a sample execution report for tracker tests."""

    return ExecutionReport(
        successful_steps=4,
        failed_steps=0,
        skipped_steps=1,
        duration_seconds=12.5,
        completed=True,
        metrics=metrics,
    )


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for tracker tests."""

    return MigrationMetrics(
        duration_seconds=12.5,
        throughput_items_per_second=0.8,
        average_item_size=2048,
        processed_bytes=10240,
        estimated_remaining_seconds=4.0,
        peak_memory_usage_mb=256.0,
    )


def test_progress_tracker_tracks_and_resets_execution_state() -> None:
    """The progress tracker should store and reset orchestration state."""

    initial_snapshot = _build_snapshot(
        processed_items=0,
        successful_items=0,
        failed_items=0,
    )
    updated_snapshot = _build_snapshot(
        processed_items=6,
        successful_items=5,
        failed_items=1,
    )
    execution_context = _build_execution_context()
    metrics = _build_metrics()
    execution_report = _build_execution_report(metrics=metrics)

    tracker = ProgressTracker(
        snapshot=initial_snapshot,
        metrics=metrics,
        execution_context=execution_context,
        execution_report=execution_report,
        migration_state=MigrationState.EXTRACTING,
    )

    assert tracker.current_snapshot == initial_snapshot
    assert tracker.current_metrics == metrics
    assert tracker.current_execution_context == execution_context
    assert tracker.current_execution_report == execution_report
    assert tracker.current_execution_report.metrics == metrics
    assert tracker.current_migration_state == MigrationState.EXTRACTING

    tracker.update_snapshot(updated_snapshot)
    tracker.update_metrics(metrics)
    tracker.update_execution_context(execution_context)
    tracker.update_execution_report(execution_report)
    updated_state: MigrationState = MigrationState.UPLOADING
    tracker.update_migration_state(updated_state)

    assert tracker.current_snapshot == updated_snapshot
    assert tracker.current_metrics == metrics
    assert tracker.current_execution_context == execution_context
    assert tracker.current_execution_report == execution_report
    assert tracker.current_execution_report.metrics == metrics
    assert tracker.current_migration_state == updated_state

    tracker.reset()

    assert tracker.current_snapshot == initial_snapshot
    assert tracker.current_metrics is None
    assert tracker.current_execution_context is None
    assert tracker.current_execution_report is None
    assert tracker.current_migration_state is None
