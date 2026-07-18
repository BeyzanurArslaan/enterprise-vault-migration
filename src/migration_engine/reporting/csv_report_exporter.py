"""CSV execution report export helpers for the migration engine.

This module exports the structured error breakdown of an execution report as a
deterministic CSV audit table. The output is intentionally flat, bounded, and
security-safe so it can be consumed by spreadsheets and downstream audit tools
without exposing raw exceptions or target payloads.
"""

from __future__ import annotations

from csv import writer
from io import StringIO

from ..contracts import ErrorBreakdownEntry, ExecutionReport
from .report_summary import resolve_final_status

_CSV_HEADER: tuple[str, ...] = (
    "export_schema_version",
    "job_id",
    "final_status",
    "completed",
    "resumed",
    "checkpoint_sequence",
    "stage",
    "category",
    "code",
    "source_identifier",
    "archive_identifier",
    "item_type",
    "retryable",
    "attempt_count",
    "message",
)

_DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@")


def execution_report_to_csv(report: ExecutionReport) -> str:
    """Serialize an execution report to a deterministic CSV audit table."""

    output = StringIO(newline="")
    csv_writer = writer(output, lineterminator="\n")
    csv_writer.writerow(_CSV_HEADER)

    for entry in report.error_breakdown:
        csv_writer.writerow(_build_row(report, entry))

    return output.getvalue()


def _build_row(report: ExecutionReport, entry: ErrorBreakdownEntry) -> list[str]:
    """Build a CSV row for a report error entry."""

    return [
        _sanitize_cell(report.export_schema_version),
        _sanitize_cell(report.job_id or ""),
        _sanitize_cell(resolve_final_status(report)),
        _boolean_text(report.completed),
        _boolean_text(report.resumed),
        _sanitize_cell(
            "" if report.checkpoint_sequence is None else str(report.checkpoint_sequence)
        ),
        _sanitize_cell(entry.stage),
        _sanitize_cell(entry.category),
        _sanitize_cell(entry.code),
        _sanitize_cell(entry.source_identifier or ""),
        _sanitize_cell(entry.archive_identifier or ""),
        _sanitize_cell(entry.item_type or ""),
        _boolean_text(entry.retryable),
        str(entry.attempt_count),
        _sanitize_cell(entry.message),
    ]


def _sanitize_cell(value: str) -> str:
    """Neutralize spreadsheet formula prefixes in a CSV cell."""

    stripped_value = value.lstrip()
    if stripped_value and stripped_value[0] in _DANGEROUS_CSV_PREFIXES:
        return f"'{value}"

    return value


def _boolean_text(value: bool | str) -> str:
    """Render booleans and strings as safe CSV text."""

    if isinstance(value, bool):
        return "true" if value else "false"

    return _sanitize_cell(value)


__all__: list[str] = ["execution_report_to_csv"]
