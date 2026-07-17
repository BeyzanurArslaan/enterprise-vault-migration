"""Regression tests for migration metrics and reporting compatibility."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from migration_engine.contracts import ExecutionReport, ProgressSnapshot
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker


def _build_snapshot() -> ProgressSnapshot:
    """Create a sample progress snapshot for metrics compatibility tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=3,
        processed_items=1,
        successful_items=1,
        failed_items=0,
        skipped_items=0,
        current_archive="archive-1",
        current_mailbox="mailbox-1",
        current_item="item-1",
        started_at=timestamp,
        last_updated=timestamp,
    )


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics instance with the extended field set."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=42.5,
        throughput_items_per_second=2.5,
        average_item_size=2048,
        processed_bytes=6144,
        estimated_remaining_seconds=8.0,
        peak_memory_usage_mb=256.0,
        total_items=3,
        processed_items=1,
        successful_items=1,
        failed_items=0,
        skipped_items=1,
        retried_items=0,
        uploaded_items=1,
        verification_failures=0,
        total_bytes=8192,
        started_at=timestamp,
        finished_at=timestamp,
    )


def test_migration_metrics_supports_extended_fields_and_defaults() -> None:
    """The metrics model should preserve compatibility and default values."""

    metrics = MigrationMetrics(
        duration_seconds=12.5,
        throughput_items_per_second=1.5,
        average_item_size=1024,
        processed_bytes=3072,
        estimated_remaining_seconds=None,
        peak_memory_usage_mb=None,
    )

    assert metrics.duration_seconds == 12.5
    assert metrics.throughput_items_per_second == 1.5
    assert metrics.average_item_size == 1024
    assert metrics.processed_bytes == 3072
    assert metrics.estimated_remaining_seconds is None
    assert metrics.peak_memory_usage_mb is None
    assert metrics.total_items == 0
    assert metrics.processed_items == 0
    assert metrics.successful_items == 0
    assert metrics.failed_items == 0
    assert metrics.skipped_items == 0
    assert metrics.retried_items == 0
    assert metrics.uploaded_items == 0
    assert metrics.verification_failures == 0
    assert metrics.rehydrated_items == 0
    assert metrics.rehydration_failures == 0
    assert metrics.rehydrated_bytes == 0
    assert metrics.sis_cache_hits == 0
    assert metrics.sis_cache_misses == 0
    assert metrics.total_bytes == 0
    assert metrics.started_at is None
    assert metrics.finished_at is None


def test_migration_metrics_are_immutable_and_work_with_reporting() -> None:
    """The metrics model should remain frozen and integrate with reporting."""

    metrics = _build_metrics()
    report = ExecutionReport(
        successful_steps=2,
        failed_steps=0,
        skipped_steps=1,
        duration_seconds=42.5,
        completed=True,
        metrics=metrics,
    )
    tracker = ProgressTracker(snapshot=_build_snapshot(), metrics=metrics, execution_report=report)

    assert report.metrics == metrics
    assert tracker.current_metrics == metrics
    assert tracker.current_execution_report == report
    assert tracker.current_execution_report.metrics == metrics

    with pytest.raises(FrozenInstanceError):
        type(metrics).__setattr__(metrics, "total_items", 99)

    with pytest.raises(FrozenInstanceError):
        type(report).__setattr__(report, "completed", False)
