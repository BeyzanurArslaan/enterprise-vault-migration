"""Upload items pipeline step module.

This module defines the pipeline step skeleton responsible for uploading
transformed items to storionX during migration execution. The current
implementation is a placeholder only and contains no migration behavior.
"""

from __future__ import annotations

from ..contracts import ExecutionContext, ExecutionReport, PipelineStep


class UploadItemsStep(PipelineStep):
    """Placeholder step for uploading transformed items."""

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare item upload for the current migration context."""

        raise NotImplementedError

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute item upload for the current migration context."""

        raise NotImplementedError

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize item upload after execution."""

        raise NotImplementedError

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback item upload after failure."""

        raise NotImplementedError


__all__: list[str] = ["UploadItemsStep"]
