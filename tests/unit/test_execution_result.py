"""Regression tests for the migration execution result contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from migration_engine.contracts import ExecutionReport
from migration_engine.execution_result import ExecutionResult
from migration_engine.metrics import MigrationMetrics


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for execution result tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=42.5,
        throughput_items_per_second=2.0,
        average_item_size=1536,
        processed_bytes=4096,
        estimated_remaining_seconds=3.0,
        peak_memory_usage_mb=192.0,
        total_items=4,
        processed_items=4,
        successful_items=4,
        failed_items=0,
        skipped_items=0,
        retried_items=1,
        uploaded_items=4,
        verification_failures=0,
        total_bytes=8192,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_report(*, metrics: MigrationMetrics) -> ExecutionReport:
    """Create a sample execution report for execution result tests."""

    return ExecutionReport(
        successful_steps=5,
        failed_steps=0,
        skipped_steps=0,
        duration_seconds=42.5,
        completed=True,
        metrics=metrics,
    )


def test_execution_result_supports_execution_summary_fields() -> None:
    """The execution result should capture immutable execution summaries."""

    metrics = _build_metrics()
    report = _build_report(metrics=metrics)
    completed_at = datetime(2026, 1, 1, 12, 1, tzinfo=UTC)
    duration = timedelta(seconds=42.5)

    result = ExecutionResult(
        success=True,
        execution_report=report,
        metrics=metrics,
        completed_at=completed_at,
        duration=duration,
        warnings=("minor-delay",),
        errors=(),
    )

    assert result.success is True
    assert result.execution_report == report
    assert result.metrics == metrics
    assert result.completed_at == completed_at
    assert result.duration == duration
    assert result.warnings == ("minor-delay",)
    assert result.errors == ()

    with pytest.raises(FrozenInstanceError):
        type(result).__setattr__(result, "success", False)
