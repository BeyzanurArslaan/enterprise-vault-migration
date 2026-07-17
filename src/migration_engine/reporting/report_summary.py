"""Execution report summary helpers for the migration engine.

This module builds the deterministic human-readable summary and final status
for the canonical execution report. The helpers are pure, target-neutral, and
safe for logs, CLI output, file export, and JSON serialization.
"""

from __future__ import annotations

from datetime import datetime

from ..contracts import ExecutionReport
from ..metrics import MigrationMetrics
from ..reconciliation import ReconciliationResult

FINAL_STATUS_COMPLETED = "completed"
FINAL_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
FINAL_STATUS_FAILED = "failed"
FINAL_STATUS_DRY_RUN_COMPLETED = "dry_run_completed"


def resolve_final_status(report: ExecutionReport) -> str:
    """Resolve the deterministic final status for an execution report."""

    if report.final_status is not None:
        return report.final_status

    if not report.completed or report.failed_steps > 0:
        return FINAL_STATUS_FAILED

    if report.reconciliation is not None and not report.reconciliation.is_reconciled:
        return FINAL_STATUS_FAILED

    if _is_dry_run_completed(report):
        return FINAL_STATUS_DRY_RUN_COMPLETED

    if _has_warnings(report):
        return FINAL_STATUS_COMPLETED_WITH_WARNINGS

    return FINAL_STATUS_COMPLETED


def build_execution_report_summary(
    report: ExecutionReport,
    *,
    checkpoint_identifier: str | None = None,
) -> str:
    """Build a deterministic human-readable summary for an execution report."""

    final_status = resolve_final_status(report)
    lines = [_status_sentence(final_status)]
    lines.append(f"Migration job ID: {report.job_id or 'unknown'}")
    lines.append(f"Final status: {final_status}")
    lines.append(f"Resumed: {'yes' if report.resumed else 'no'}")
    if checkpoint_identifier is not None:
        lines.append(f"Checkpoint ID: {checkpoint_identifier}")
    elif report.checkpoint_sequence is not None:
        lines.append(f"Checkpoint sequence: {report.checkpoint_sequence}")
    else:
        lines.append("Checkpoint sequence: n/a")
    lines.append(f"Started at: {_format_datetime(report.started_at)}")
    lines.append(f"Completed at: {_format_datetime(report.completed_at)}")
    lines.append(f"Duration seconds: {_format_number(report.duration_seconds)}")
    lines.append(f"Archives discovered: {report.discovered_archives}")
    lines.append(f"Items extracted: {report.extracted_items}")
    lines.append(f"Items transformed: {report.transformed_items}")
    lines.append(f"Items uploaded: {_resolve_uploaded_items(report.metrics)}")
    lines.append(f"Idempotent replays: {_resolve_idempotent_replays(report.metrics)}")
    lines.append(f"Items verified: {_resolve_verified_items(report.reconciliation)}")
    lines.append(f"Retries: {_resolve_retries(report.metrics)}")
    lines.append(f"Failed items: {_resolve_failed_items(report.metrics)}")
    lines.append(f"Dry-run items: {_resolve_dry_run_items(report.metrics)}")
    lines.append(f"Missing items: {_resolve_missing_items(report.reconciliation)}")
    lines.append(
        f"Checksum mismatches: {_resolve_checksum_mismatches(report.reconciliation)}",
    )
    reconciliation_status = (
        report.reconciliation.status if report.reconciliation is not None else "n/a"
    )
    lines.append(f"Reconciliation status: {reconciliation_status}")
    lines.append(f"Reconciled: {'yes' if _is_reconciled(report) else 'no'}")
    lines.append(f"Warnings: {len(report.warnings)}")
    lines.append(f"Archive filters: {_format_scope(report.archive_names)}")
    lines.append(f"Folder filters: {_format_scope(report.folder_paths)}")
    lines.append(f"Start date filter: {_format_datetime(report.start_date)}")
    lines.append(f"End date filter: {_format_datetime(report.end_date)}")

    return "\n".join(lines)


def _status_sentence(final_status: str) -> str:
    """Return the human-readable opening sentence for a final status."""

    if final_status == FINAL_STATUS_COMPLETED:
        return "Migration completed successfully."
    if final_status == FINAL_STATUS_COMPLETED_WITH_WARNINGS:
        return "Migration completed with warnings."
    if final_status == FINAL_STATUS_DRY_RUN_COMPLETED:
        return "Dry-run migration completed successfully without target mutation."
    return "Migration failed."


def _format_datetime(value: object | None) -> str:
    """Format an optional datetime-like value for deterministic reporting."""

    if value is None:
        return "n/a"

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def _format_number(value: float) -> str:
    """Format a floating-point number without trailing zero noise."""

    rendered = f"{value:.6f}"
    rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _format_scope(values: tuple[str, ...] | None) -> str:
    """Format a filter scope while preserving the difference between None and empty."""

    if values is None:
        return "all"

    if len(values) == 0:
        return "explicitly empty"

    return ", ".join(values)


def _is_dry_run_completed(report: ExecutionReport) -> bool:
    """Return whether the report represents a completed dry-run execution."""

    metrics = report.metrics
    if metrics is None:
        return False

    if metrics.dry_run_items <= 0:
        return False

    return metrics.uploaded_items == 0 and report.reconciliation is not None


def _has_warnings(report: ExecutionReport) -> bool:
    """Return whether the report contains non-terminal warning signals."""

    metrics = report.metrics
    if metrics is None:
        return bool(report.warnings)

    return bool(
        report.warnings
        or metrics.retried_items > 0
        or metrics.failed_items > 0
        or metrics.verification_failures > 0
        or metrics.dry_run_items > 0
    )


def _is_reconciled(report: ExecutionReport) -> bool:
    """Return whether the report reconciliation resolved successfully."""

    reconciliation = report.reconciliation
    if reconciliation is None:
        return False

    return reconciliation.is_reconciled


def _resolve_uploaded_items(metrics: MigrationMetrics | None) -> int:
    """Return the number of uploaded items represented by the metrics."""

    if metrics is None:
        return 0

    return metrics.uploaded_items


def _resolve_idempotent_replays(metrics: MigrationMetrics | None) -> int:
    """Return the number of idempotent replayed uploads represented by the metrics."""

    if metrics is None:
        return 0

    return metrics.idempotent_replays


def _resolve_retries(metrics: MigrationMetrics | None) -> int:
    """Return the number of retries represented by the metrics."""

    if metrics is None:
        return 0

    return metrics.retried_items


def _resolve_failed_items(metrics: MigrationMetrics | None) -> int:
    """Return the number of failed items represented by the metrics."""

    if metrics is None:
        return 0

    return metrics.failed_items


def _resolve_dry_run_items(metrics: MigrationMetrics | None) -> int:
    """Return the number of dry-run items represented by the metrics."""

    if metrics is None:
        return 0

    return metrics.dry_run_items


def _resolve_verified_items(reconciliation: ReconciliationResult | None) -> int:
    """Return the number of verified items represented by the reconciliation result."""

    if reconciliation is None:
        return 0

    return reconciliation.verified_items


def _resolve_missing_items(reconciliation: ReconciliationResult | None) -> int:
    """Return the number of missing items represented by the reconciliation result."""

    if reconciliation is None:
        return 0

    return len(reconciliation.missing_items)


def _resolve_checksum_mismatches(
    reconciliation: ReconciliationResult | None,
) -> int:
    """Return the number of checksum mismatches represented by the reconciliation result."""

    if reconciliation is None:
        return 0

    return len(reconciliation.checksum_mismatches)


__all__: list[str] = [
    "FINAL_STATUS_COMPLETED",
    "FINAL_STATUS_COMPLETED_WITH_WARNINGS",
    "FINAL_STATUS_DRY_RUN_COMPLETED",
    "FINAL_STATUS_FAILED",
    "build_execution_report_summary",
    "resolve_final_status",
]
