"""JSON execution report export helpers for the migration engine.

This module provides the canonical JSON serialization entry point for
execution reports. The exporter keeps the output deterministic, UTF-8 safe,
and free from infrastructure-specific types by delegating to the canonical
report dictionary serializer.
"""

from __future__ import annotations

import json

from ..contracts import ExecutionReport
from .report_formatter import execution_report_to_dict


def execution_report_to_json(report: ExecutionReport) -> str:
    """Serialize an execution report to a deterministic JSON document."""

    return json.dumps(
        execution_report_to_dict(report),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


__all__: list[str] = ["execution_report_to_json"]
