"""Finalize migration pipeline step module.

This module defines the pipeline step skeleton responsible for finalizing a
migration run after all processing stages complete. The current implementation
is a placeholder only and contains no migration behavior.
"""

from __future__ import annotations

from ..contracts import ExecutionContext, ExecutionReport, PipelineStep


class FinalizeMigrationStep(PipelineStep):
    """Placeholder step for finalizing the migration workflow."""

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare finalization for the current migration context."""

        raise NotImplementedError

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute finalization for the current migration context."""

        raise NotImplementedError

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize the migration run after execution."""

        raise NotImplementedError

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback migration finalization after failure."""

        raise NotImplementedError


__all__: list[str] = ["FinalizeMigrationStep"]
