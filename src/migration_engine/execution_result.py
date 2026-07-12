"""Migration execution result module for the migration engine foundation.

This module defines the placeholder result type that will later capture the
outcome of a migration run. The result remains an immutable contract only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .contracts import ExecutionReport
from .metrics import MigrationMetrics


@dataclass(slots=True, frozen=True)
class ExecutionResult:
    """Immutable summary of a migration execution outcome."""

    success: bool
    execution_report: ExecutionReport | None = None
    metrics: MigrationMetrics | None = None
    completed_at: datetime | None = None
    duration: timedelta | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


__all__: list[str] = ["ExecutionResult"]
