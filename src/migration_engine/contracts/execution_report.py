"""Migration execution report contract module.

This module defines the immutable summary object produced by a migration
pipeline run. The report captures high-level execution outcomes, can carry
optional metrics for reporting compatibility, and exposes the active
migration filters applied to the execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..metrics import MigrationMetrics
from ..reconciliation import ReconciliationResult


@dataclass(slots=True, frozen=True)
class ExecutionReport:
    """Immutable summary of a migration pipeline execution."""

    successful_steps: int
    failed_steps: int
    skipped_steps: int
    duration_seconds: float
    completed: bool
    metrics: MigrationMetrics | None = None
    reconciliation: ReconciliationResult | None = None
    archive_names: tuple[str, ...] | None = None
    folder_paths: tuple[str, ...] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


__all__: list[str] = ["ExecutionReport"]
