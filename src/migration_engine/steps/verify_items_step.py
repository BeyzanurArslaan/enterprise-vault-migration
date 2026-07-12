"""Verify items pipeline step module.

This module defines the pipeline step skeleton responsible for verifying
uploaded items in storionX during migration execution. The current
implementation is a placeholder only and contains no migration behavior.
"""

from __future__ import annotations

from ..contracts import ExecutionContext, ExecutionReport, PipelineStep


class VerifyItemsStep(PipelineStep):
    """Placeholder step for verifying uploaded items."""

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare item verification for the current migration context."""

        raise NotImplementedError

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute item verification for the current migration context."""

        raise NotImplementedError

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize item verification after execution."""

        raise NotImplementedError

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback item verification after failure."""

        raise NotImplementedError


__all__: list[str] = ["VerifyItemsStep"]
