"""Extract items pipeline step module.

This module defines the pipeline step skeleton responsible for extracting
items from discovered source archives during migration execution. The current
implementation is a placeholder only and contains no migration behavior.
"""

from __future__ import annotations

from ..contracts import ExecutionContext, ExecutionReport, PipelineStep


class ExtractItemsStep(PipelineStep):
    """Placeholder step for extracting items from archives."""

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare item extraction for the current migration context."""

        raise NotImplementedError

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute item extraction for the current migration context."""

        raise NotImplementedError

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize item extraction after execution."""

        raise NotImplementedError

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback item extraction after failure."""

        raise NotImplementedError


__all__: list[str] = ["ExtractItemsStep"]
