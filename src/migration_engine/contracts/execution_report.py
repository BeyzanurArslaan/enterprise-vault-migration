"""Migration execution report contract module.

This module defines the immutable summary object produced by a migration
pipeline run. The report captures high-level execution outcomes and can carry
optional metrics for reporting compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..metrics import MigrationMetrics


@dataclass(slots=True, frozen=True)
class ExecutionReport:
    """Immutable summary of a migration pipeline execution."""

    successful_steps: int
    failed_steps: int
    skipped_steps: int
    duration_seconds: float
    completed: bool
    metrics: MigrationMetrics | None = None


__all__: list[str] = ["ExecutionReport"]
