"""Regression tests for the migration execution context contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ProgressSnapshot
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState


def _build_snapshot() -> ProgressSnapshot:
    """Create a sample progress snapshot for execution context tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=5,
        processed_items=2,
        successful_items=2,
        failed_items=0,
        skipped_items=0,
        current_archive="archive-1",
        current_mailbox="mailbox-1",
        current_item="item-1",
        started_at=timestamp,
        last_updated=timestamp,
    )


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for execution context tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=18.5,
        throughput_items_per_second=1.2,
        average_item_size=1024,
        processed_bytes=2048,
        estimated_remaining_seconds=5.0,
        peak_memory_usage_mb=128.0,
        total_items=5,
        processed_items=2,
        successful_items=2,
        failed_items=0,
        skipped_items=0,
        retried_items=0,
        uploaded_items=2,
        verification_failures=0,
        total_bytes=4096,
        started_at=timestamp,
        finished_at=None,
    )


def test_execution_context_supports_extended_state_fields() -> None:
    """The execution context should carry compatible orchestration state."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    metrics = _build_metrics()
    tracker = ProgressTracker(snapshot=_build_snapshot(), metrics=metrics)

    context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=timestamp,
        current_step="discover",
        metrics=metrics,
        progress_tracker=tracker,
        state=MigrationState.DISCOVERING,
        current_timestamp=timestamp,
    )

    tracker.update_execution_context(context)

    assert context.migration_id == "migration-1"
    assert context.configuration is not None
    assert context.started_at == timestamp
    assert context.current_step == "discover"
    assert context.metrics == metrics
    assert context.progress_tracker is tracker
    assert context.state == MigrationState.DISCOVERING
    assert context.current_timestamp == timestamp
    assert tracker.current_execution_context is context

    with pytest.raises(FrozenInstanceError):
        type(context).__setattr__(context, "current_step", "uploading")
