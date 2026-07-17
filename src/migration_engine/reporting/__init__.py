"""Reporting helpers for the migration engine.

This package exposes the canonical execution report formatter and JSON-safe
serialization helpers used by the final migration reporting stage.
"""

from __future__ import annotations

from .report_formatter import execution_report_to_dict, format_execution_report
from .report_summary import (
    FINAL_STATUS_COMPLETED,
    FINAL_STATUS_COMPLETED_WITH_WARNINGS,
    FINAL_STATUS_DRY_RUN_COMPLETED,
    FINAL_STATUS_FAILED,
    build_execution_report_summary,
    resolve_final_status,
)

__all__: list[str] = [
    "FINAL_STATUS_COMPLETED",
    "FINAL_STATUS_COMPLETED_WITH_WARNINGS",
    "FINAL_STATUS_DRY_RUN_COMPLETED",
    "FINAL_STATUS_FAILED",
    "build_execution_report_summary",
    "execution_report_to_dict",
    "format_execution_report",
    "resolve_final_status",
]
