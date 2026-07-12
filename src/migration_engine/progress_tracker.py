"""Migration progress tracker module for the migration engine foundation.

This module defines the orchestration-oriented tracker that keeps the current
progress snapshot together with optional execution metadata captured during a
migration run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from .metrics import MigrationMetrics
from .state_machine import MigrationState


@dataclass(slots=True, init=False)
class ProgressTracker:
    """Track migration progress snapshots and execution metadata."""

    _initial_snapshot: ProgressSnapshot = field(repr=False)
    _current_snapshot: ProgressSnapshot = field(repr=False)
    _current_metrics: MigrationMetrics | None = field(default=None, repr=False)
    _current_execution_context: ExecutionContext | None = field(default=None, repr=False)
    _current_execution_report: ExecutionReport | None = field(default=None, repr=False)
    _current_migration_state: MigrationState | None = field(default=None, repr=False)

    def __init__(
        self,
        *,
        snapshot: ProgressSnapshot,
        metrics: MigrationMetrics | None = None,
        execution_context: ExecutionContext | None = None,
        execution_report: ExecutionReport | None = None,
        migration_state: MigrationState | None = None,
    ) -> None:
        """Create a tracker seeded with the initial progress snapshot."""

        self._initial_snapshot = snapshot
        self._current_snapshot = snapshot
        self._current_metrics = metrics
        self._current_execution_context = execution_context
        self._current_execution_report = execution_report
        self._current_migration_state = migration_state

    @property
    def current_snapshot(self) -> ProgressSnapshot:
        """Return the active progress snapshot."""

        return self._current_snapshot

    @property
    def current_metrics(self) -> MigrationMetrics | None:
        """Return the most recent execution metrics."""

        return self._current_metrics

    @property
    def current_execution_context(self) -> ExecutionContext | None:
        """Return the current execution context."""

        return self._current_execution_context

    @property
    def current_execution_report(self) -> ExecutionReport | None:
        """Return the latest execution report."""

        return self._current_execution_report

    @property
    def current_migration_state(self) -> MigrationState | None:
        """Return the current migration state."""

        return self._current_migration_state

    def update_snapshot(self, snapshot: ProgressSnapshot) -> None:
        """Replace the active progress snapshot."""

        self._current_snapshot = snapshot

    def update_metrics(self, metrics: MigrationMetrics) -> None:
        """Record the latest execution metrics."""

        self._current_metrics = metrics

    def update_execution_context(self, execution_context: ExecutionContext) -> None:
        """Record the current execution context."""

        self._current_execution_context = execution_context

    def update_execution_report(self, execution_report: ExecutionReport) -> None:
        """Record the latest execution report."""

        self._current_execution_report = execution_report

    def update_migration_state(self, migration_state: MigrationState) -> None:
        """Record the current migration state."""

        self._current_migration_state = migration_state

    def reset(self) -> None:
        """Restore the tracker to its initial progress state."""

        self._current_snapshot = self._initial_snapshot
        self._current_metrics = None
        self._current_execution_context = None
        self._current_execution_report = None
        self._current_migration_state = None


__all__: list[str] = ["ProgressTracker"]
