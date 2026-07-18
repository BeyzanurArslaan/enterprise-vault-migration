"""Regression tests for JSON and CSV migration report exports.

This module verifies that the report export helpers remain deterministic,
security-safe, and aligned with the canonical execution report contract.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from io import StringIO

from migration_engine.contracts import ErrorBreakdownEntry, ExecutionReport
from migration_engine.reporting import (
    execution_report_to_csv,
    execution_report_to_dict,
    execution_report_to_json,
)


def _build_report(
    *,
    error_breakdown: tuple[ErrorBreakdownEntry, ...],
    completed: bool = True,
    final_status: str | None = "completed_with_warnings",
) -> ExecutionReport:
    """Create a deterministic execution report for export tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ExecutionReport(
        successful_steps=1,
        failed_steps=0,
        skipped_steps=0,
        duration_seconds=12.5,
        completed=completed,
        job_id="migration-1",
        started_at=timestamp,
        completed_at=timestamp,
        resumed=False,
        checkpoint_sequence=3,
        warnings=("retry occurred",),
        final_status=final_status,
        error_breakdown=error_breakdown,
        export_schema_version="1",
        archive_names=("Archive One",),
        folder_paths=("Finance",),
        metrics=None,
        reconciliation=None,
    )


def test_execution_report_json_export_is_deterministic_and_safe() -> None:
    """The JSON export should remain deterministic and security-safe."""

    report = _build_report(
        error_breakdown=(
            ErrorBreakdownEntry(
                source_identifier="message-1",
                stage="upload",
                category="upload",
                code="upload_failed",
                message="Upload failed for a transformed document.",
                retryable=False,
                attempt_count=1,
                final_status="completed_with_warnings",
                archive_identifier="Archive One",
                item_type="email",
            ),
            ErrorBreakdownEntry(
                source_identifier="message-2",
                stage="verification",
                category="verification",
                code="checksum_mismatch",
                message="Target document checksum mismatched during verification.",
                retryable=False,
                attempt_count=1,
                final_status="completed_with_warnings",
                archive_identifier="Archive One",
                item_type="email",
            ),
        ),
    )

    payload = execution_report_to_json(report)
    repeated_payload = execution_report_to_json(report)
    report_dict = execution_report_to_dict(report)
    parsed_payload = json.loads(payload)

    assert payload == repeated_payload
    assert parsed_payload == report_dict
    assert parsed_payload["export_schema_version"] == "1"
    assert parsed_payload["error_breakdown"][0]["stage"] == "upload"
    assert parsed_payload["error_breakdown"][1]["code"] == "checksum_mismatch"
    assert "mock_storionx" not in payload
    assert "secret" not in payload


def test_execution_report_csv_export_is_deterministic_and_sanitized() -> None:
    """The CSV export should remain deterministic and neutralize formulas."""

    report = _build_report(
        error_breakdown=(
            ErrorBreakdownEntry(
                source_identifier="+source",
                stage="pipeline",
                category="pipeline",
                code="step_failed",
                message="=SUM(1,1)",
                retryable=True,
                attempt_count=2,
                final_status="failed",
                archive_identifier="@Archive",
                item_type="-email",
            ),
        ),
        final_status="failed",
        completed=False,
    )

    payload = execution_report_to_csv(report)
    repeated_payload = execution_report_to_csv(report)
    rows = list(csv.reader(StringIO(payload)))
    repeated_rows = list(csv.reader(StringIO(repeated_payload)))

    assert payload == repeated_payload
    assert rows == repeated_rows
    assert rows[0] == [
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
    ]
    assert len(rows) == 2
    assert rows[1][0] == "1"
    assert rows[1][1] == "migration-1"
    assert rows[1][2] == "failed"
    assert rows[1][9].startswith("'")
    assert rows[1][10].startswith("'")
    assert rows[1][11].startswith("'")
    assert rows[1][14].startswith("'")


def test_execution_report_csv_export_returns_header_when_empty() -> None:
    """The CSV export should produce a valid header-only document when empty."""

    report = _build_report(error_breakdown=(), final_status="completed")
    rows = list(csv.reader(StringIO(execution_report_to_csv(report))))

    assert rows == [
        [
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
        ],
    ]
