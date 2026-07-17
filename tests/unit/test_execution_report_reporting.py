"""Regression tests for final migration reporting.

This module verifies that the canonical execution report remains backward
compatible while supporting deterministic final status resolution, summary
rendering, and JSON-safe serialization.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast

import pytest

from migration_engine.contracts import ExecutionReport
from migration_engine.metrics import MigrationMetrics
from migration_engine.reconciliation import ReconciliationResult
from migration_engine.reporting import (
    FINAL_STATUS_COMPLETED,
    FINAL_STATUS_COMPLETED_WITH_WARNINGS,
    FINAL_STATUS_DRY_RUN_COMPLETED,
    FINAL_STATUS_FAILED,
    build_execution_report_summary,
    execution_report_to_dict,
    format_execution_report,
    resolve_final_status,
)


def _build_metrics(
    *,
    retried_items: int = 0,
    idempotent_replays: int = 0,
    dry_run_items: int = 0,
    failed_items: int = 0,
    verification_failures: int = 0,
    uploaded_items: int = 2,
) -> MigrationMetrics:
    """Create deterministic metrics for report tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=12.5,
        throughput_items_per_second=2.5,
        average_item_size=2048,
        processed_bytes=6144,
        estimated_remaining_seconds=None,
        peak_memory_usage_mb=None,
        total_items=2,
        processed_items=2,
        successful_items=2,
        failed_items=failed_items,
        skipped_items=0,
        filtered_archives=0,
        filtered_items=0,
        retried_items=retried_items,
        idempotent_replays=idempotent_replays,
        dry_run_items=dry_run_items,
        reconciled_items=2,
        missing_items=0,
        checksum_mismatches=0,
        uploaded_items=uploaded_items,
        verification_failures=verification_failures,
        total_bytes=8192,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_reconciliation(
    *,
    status: str = "reconciled",
    is_reconciled: bool = True,
    missing_items: tuple[str, ...] = (),
    checksum_mismatches: tuple[str, ...] = (),
) -> ReconciliationResult:
    """Create deterministic reconciliation data for report tests."""

    return ReconciliationResult(
        expected_items=2,
        uploaded_items=2,
        verified_items=2,
        idempotent_replays=0,
        dry_run_items=0,
        missing_items=missing_items,
        unexpected_items=(),
        checksum_mismatches=checksum_mismatches,
        status=status,
        is_reconciled=is_reconciled,
    )


def _build_report(
    *,
    metrics: MigrationMetrics | None = None,
    reconciliation: ReconciliationResult | None = None,
    archive_names: tuple[str, ...] | None = ("Archive One", "Archive Two"),
    folder_paths: tuple[str, ...] | None = ("Finance", "Legal"),
    start_date: datetime | None = datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
    end_date: datetime | None = datetime(2026, 1, 31, 18, 0, tzinfo=UTC),
    final_status: str | None = None,
    warnings: tuple[str, ...] = (),
    resumed: bool = False,
    summary: str | None = None,
    discovered_archives: int = 3,
    extracted_items: int = 120,
    transformed_items: int = 118,
    job_id: str | None = "migration-1",
    checkpoint_sequence: int | None = 7,
    started_at: datetime | None = datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    completed_at: datetime | None = datetime(2026, 1, 1, 12, 1, tzinfo=UTC),
    completed: bool = True,
) -> ExecutionReport:
    """Create a deterministic execution report for report tests."""

    resolved_metrics = metrics or _build_metrics()
    resolved_reconciliation = reconciliation or _build_reconciliation()
    return ExecutionReport(
        successful_steps=6 if completed else 5,
        failed_steps=0 if completed else 1,
        skipped_steps=0,
        duration_seconds=60.0,
        completed=completed,
        job_id=job_id,
        started_at=started_at,
        completed_at=completed_at,
        resumed=resumed,
        checkpoint_sequence=checkpoint_sequence,
        discovered_archives=discovered_archives,
        extracted_items=extracted_items,
        transformed_items=transformed_items,
        warnings=warnings,
        final_status=final_status,
        summary=summary,
        metrics=resolved_metrics,
        reconciliation=resolved_reconciliation,
        archive_names=archive_names,
        folder_paths=folder_paths,
        start_date=start_date,
        end_date=end_date,
    )


def test_execution_report_supports_backward_compatible_defaults() -> None:
    """The execution report should preserve existing defaults and immutability."""

    report = ExecutionReport(
        successful_steps=0,
        failed_steps=0,
        skipped_steps=0,
        duration_seconds=0.0,
        completed=False,
    )

    assert report.job_id is None
    assert report.started_at is None
    assert report.completed_at is None
    assert report.resumed is False
    assert report.checkpoint_sequence is None
    assert report.discovered_archives == 0
    assert report.extracted_items == 0
    assert report.transformed_items == 0
    assert report.warnings == ()
    assert report.final_status is None
    assert report.summary is None
    assert report.metrics is None
    assert report.reconciliation is None
    assert report.archive_names is None
    assert report.folder_paths is None
    assert report.start_date is None
    assert report.end_date is None

    with pytest.raises(FrozenInstanceError):
        type(report).__setattr__(report, "completed", True)


@pytest.mark.parametrize(
    ("report", "expected_status"),
    [
        pytest.param(_build_report(final_status=None), FINAL_STATUS_COMPLETED, id="completed"),
        pytest.param(
            _build_report(
                metrics=_build_metrics(retried_items=1),
                warnings=("retry occurred",),
                final_status=None,
            ),
            FINAL_STATUS_COMPLETED_WITH_WARNINGS,
            id="warnings",
        ),
        pytest.param(
            _build_report(
                metrics=_build_metrics(dry_run_items=2, uploaded_items=0),
                reconciliation=_build_reconciliation(status="dry_run_reconciled"),
                final_status=None,
            ),
            FINAL_STATUS_DRY_RUN_COMPLETED,
            id="dry-run",
        ),
        pytest.param(
            _build_report(
                completed=True,
                reconciliation=_build_reconciliation(
                    status="needs_review",
                    is_reconciled=False,
                    missing_items=("message-2",),
                    checksum_mismatches=("message-2",),
                ),
                final_status=None,
            ),
            FINAL_STATUS_FAILED,
            id="failed",
        ),
    ],
)
def test_execution_report_final_status_resolution(
    report: ExecutionReport,
    expected_status: str,
) -> None:
    """Final status resolution should remain deterministic."""

    assert resolve_final_status(report) == expected_status


def test_execution_report_summary_and_dict_are_deterministic() -> None:
    """The summary and dictionary representation should remain deterministic."""

    report = _build_report(
        metrics=_build_metrics(retried_items=2, idempotent_replays=1, uploaded_items=1),
        reconciliation=_build_reconciliation(),
        warnings=("retry occurred",),
        resumed=True,
    )

    summary = format_execution_report(report)
    repeated_summary = format_execution_report(report)
    summary_lines = summary.splitlines()

    assert summary == repeated_summary
    assert summary_lines == [
        "Migration completed with warnings.",
        "Migration job ID: migration-1",
        "Final status: completed_with_warnings",
        "Resumed: yes",
        "Checkpoint sequence: 7",
        "Started at: 2026-01-01T12:00:00+00:00",
        "Completed at: 2026-01-01T12:01:00+00:00",
        "Duration seconds: 60",
        "Archives discovered: 3",
        "Items extracted: 120",
        "Items transformed: 118",
        "Items uploaded: 1",
        "Idempotent replays: 1",
        "Items verified: 2",
        "Retries: 2",
        "Failed items: 0",
        "Dry-run items: 0",
        "Missing items: 0",
        "Checksum mismatches: 0",
        "Reconciliation status: reconciled",
        "Reconciled: yes",
        "Warnings: 1",
        "Archive filters: Archive One, Archive Two",
        "Folder filters: Finance, Legal",
        "Start date filter: 2026-01-01T08:00:00+00:00",
        "End date filter: 2026-01-31T18:00:00+00:00",
    ]

    report_dict = execution_report_to_dict(report)
    repeated_dict = execution_report_to_dict(report)
    json_payload = json.dumps(report_dict, sort_keys=True)

    assert report_dict == repeated_dict
    assert report_dict["job_id"] == "migration-1"
    assert report_dict["final_status"] == FINAL_STATUS_COMPLETED_WITH_WARNINGS
    assert report_dict["resumed"] is True
    assert report_dict["summary"] == summary
    timing = cast(dict[str, object], report_dict["timing"])
    scope = cast(dict[str, object], report_dict["scope"])
    metrics = cast(dict[str, object], report_dict["metrics"])
    reconciliation = cast(dict[str, object], report_dict["reconciliation"])
    assert timing["started_at"] == "2026-01-01T12:00:00+00:00"
    assert timing["completed_at"] == "2026-01-01T12:01:00+00:00"
    assert scope["discovered_archives"] == 3
    assert metrics["retried_items"] == 2
    assert reconciliation["status"] == "reconciled"
    assert "mock_storionx" not in json_payload
    assert "secret" not in json_payload


def test_execution_report_handles_empty_filters_and_dry_run_summary() -> None:
    """The summary should distinguish no filters from explicit empty filters."""

    report = _build_report(
        metrics=_build_metrics(dry_run_items=2, uploaded_items=0),
        reconciliation=_build_reconciliation(status="dry_run_reconciled"),
        archive_names=(),
        folder_paths=None,
        start_date=None,
        end_date=None,
        final_status=None,
    )

    summary = build_execution_report_summary(report)
    report_dict = execution_report_to_dict(report)

    assert summary.splitlines()[0] == (
        "Dry-run migration completed successfully without target mutation."
    )
    assert "Archive filters: explicitly empty" in summary
    assert "Folder filters: all" in summary
    assert "Dry-run items: 2" in summary
    filters = cast(dict[str, object], report_dict["filters"])
    assert filters["archive_names"] == []
    assert filters["folder_paths"] is None


def test_execution_report_excludes_sensitive_payloads() -> None:
    """The report should not surface secret or payload content in its summary."""

    report = _build_report(
        summary=None,
        archive_names=("Archive One",),
        folder_paths=("Finance",),
        final_status=None,
    )

    summary = format_execution_report(report)
    report_dict = execution_report_to_dict(report)

    assert "password" not in summary
    assert "token" not in summary
    assert "Body" not in summary
    assert "password" not in json.dumps(report_dict, sort_keys=True)
    assert "token" not in json.dumps(report_dict, sort_keys=True)
