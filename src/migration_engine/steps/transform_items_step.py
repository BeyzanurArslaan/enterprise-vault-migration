"""Transform items pipeline step module.

This module defines the pipeline step skeleton responsible for transforming
extracted items into the target storionX shape. The current implementation is
placeholder only and contains no migration behavior.
"""

from __future__ import annotations

from ..contracts import ExecutionContext, ExecutionReport, PipelineStep


class TransformItemsStep(PipelineStep):
    """Placeholder step for transforming extracted items."""

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare item transformation for the current migration context."""

        raise NotImplementedError

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute item transformation for the current migration context."""

        raise NotImplementedError

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize item transformation after execution."""

        raise NotImplementedError

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback item transformation after failure."""

        raise NotImplementedError


__all__: list[str] = ["TransformItemsStep"]
