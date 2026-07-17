"""Execution report formatter for the migration engine.

This module exposes the canonical formatting and serialization helpers for the
final migration report. The helpers are pure, deterministic, and target
neutral so they can be reused by tests, CLI output, APIs, and file export
layers without introducing orchestration or persistence coupling.
"""

from __future__ import annotations

from datetime import datetime

from ..contracts import ExecutionReport
from ..metrics import MigrationMetrics
from ..reconciliation import ReconciliationResult
from .report_summary import build_execution_report_summary, resolve_final_status


def format_execution_report(report: ExecutionReport) -> str:
    """Format an execution report as a deterministic human-readable summary."""

    if report.summary is not None:
        return report.summary

    return build_execution_report_summary(report)


def execution_report_to_dict(report: ExecutionReport) -> dict[str, object]:
    """Serialize an execution report into a JSON-safe deterministic dictionary."""

    summary = format_execution_report(report)
    return {
        "job_id": report.job_id,
        "final_status": resolve_final_status(report),
        "completed": report.completed,
        "resumed": report.resumed,
        "checkpoint_sequence": report.checkpoint_sequence,
        "summary": summary,
        "timing": {
            "started_at": _serialize_datetime(report.started_at),
            "completed_at": _serialize_datetime(report.completed_at),
            "duration_seconds": report.duration_seconds,
        },
        "scope": {
            "discovered_archives": report.discovered_archives,
            "extracted_items": report.extracted_items,
            "transformed_items": report.transformed_items,
        },
        "filters": {
            "archive_names": _serialize_tuple(report.archive_names),
            "folder_paths": _serialize_tuple(report.folder_paths),
            "start_date": _serialize_datetime(report.start_date),
            "end_date": _serialize_datetime(report.end_date),
        },
        "warnings": list(report.warnings),
        "metrics": _serialize_metrics(report.metrics),
        "reconciliation": _serialize_reconciliation(report.reconciliation),
    }


def _serialize_datetime(value: datetime | None) -> str | None:
    """Serialize an optional datetime into an ISO 8601 string."""

    if value is None:
        return None

    return value.isoformat()


def _serialize_tuple(values: tuple[str, ...] | None) -> list[str] | None:
    """Serialize a tuple of strings into a JSON-safe list."""

    if values is None:
        return None

    return list(values)


def _serialize_metrics(metrics: MigrationMetrics | None) -> dict[str, object] | None:
    """Serialize metrics into a JSON-safe dictionary."""

    if metrics is None:
        return None

    return {
        "duration_seconds": metrics.duration_seconds,
        "throughput_items_per_second": metrics.throughput_items_per_second,
        "average_item_size": metrics.average_item_size,
        "processed_bytes": metrics.processed_bytes,
        "estimated_remaining_seconds": metrics.estimated_remaining_seconds,
        "peak_memory_usage_mb": metrics.peak_memory_usage_mb,
        "total_items": metrics.total_items,
        "processed_items": metrics.processed_items,
        "successful_items": metrics.successful_items,
        "failed_items": metrics.failed_items,
        "skipped_items": metrics.skipped_items,
        "filtered_archives": metrics.filtered_archives,
        "filtered_items": metrics.filtered_items,
        "retried_items": metrics.retried_items,
        "idempotent_replays": metrics.idempotent_replays,
        "dry_run_items": metrics.dry_run_items,
        "rehydrated_items": metrics.rehydrated_items,
        "rehydration_failures": metrics.rehydration_failures,
        "rehydrated_bytes": metrics.rehydrated_bytes,
        "sis_cache_hits": metrics.sis_cache_hits,
        "sis_cache_misses": metrics.sis_cache_misses,
        "reconciled_items": metrics.reconciled_items,
        "missing_items": metrics.missing_items,
        "checksum_mismatches": metrics.checksum_mismatches,
        "uploaded_items": metrics.uploaded_items,
        "verification_failures": metrics.verification_failures,
        "total_bytes": metrics.total_bytes,
        "started_at": _serialize_datetime(metrics.started_at),
        "finished_at": _serialize_datetime(metrics.finished_at),
    }


def _serialize_reconciliation(
    reconciliation: ReconciliationResult | None,
) -> dict[str, object] | None:
    """Serialize reconciliation results into a JSON-safe dictionary."""

    if reconciliation is None:
        return None

    return {
        "expected_items": reconciliation.expected_items,
        "uploaded_items": reconciliation.uploaded_items,
        "verified_items": reconciliation.verified_items,
        "idempotent_replays": reconciliation.idempotent_replays,
        "dry_run_items": reconciliation.dry_run_items,
        "missing_items": list(reconciliation.missing_items),
        "unexpected_items": list(reconciliation.unexpected_items),
        "checksum_mismatches": list(reconciliation.checksum_mismatches),
        "status": reconciliation.status,
        "is_reconciled": reconciliation.is_reconciled,
    }


__all__: list[str] = [
    "execution_report_to_dict",
    "format_execution_report",
]
