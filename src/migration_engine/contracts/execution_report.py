"""Migration execution report contract module.

This module defines the immutable summary object produced by a migration
pipeline run. The report captures high-level execution outcomes, can carry
optional metrics for reporting compatibility, and exposes the active
migration filters applied to the execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from ..metrics import MigrationMetrics
from ..reconciliation import ReconciliationResult

if TYPE_CHECKING:
    from .error_breakdown import ErrorBreakdownEntry


@dataclass(slots=True, frozen=True)
class ExecutionReport:
    """Immutable summary of a migration pipeline execution."""

    successful_steps: int
    failed_steps: int
    skipped_steps: int
    duration_seconds: float
    completed: bool
    job_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    resumed: bool = False
    checkpoint_sequence: int | None = None
    discovered_archives: int = 0
    extracted_items: int = 0
    transformed_items: int = 0
    warnings: tuple[str, ...] = ()
    final_status: str | None = None
    summary: str | None = None
    error_breakdown: tuple[ErrorBreakdownEntry, ...] = ()
    export_schema_version: str = "1"
    metrics: MigrationMetrics | None = None
    reconciliation: ReconciliationResult | None = None
    archive_names: tuple[str, ...] | None = None
    folder_paths: tuple[str, ...] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


__all__: list[str] = ["ExecutionReport"]
