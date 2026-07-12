"""Migration execution report contract module.

This module defines the immutable summary object produced by a migration
pipeline run. The report captures only high-level execution outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ExecutionReport:
    """Immutable summary of a migration pipeline execution."""

    successful_steps: int
    failed_steps: int
    skipped_steps: int
    duration_seconds: float
    completed: bool


__all__: list[str] = ["ExecutionReport"]
