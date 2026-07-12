"""Discover archives pipeline step module.

This module defines the pipeline step skeleton responsible for discovering
source archives during migration execution. The current implementation is a
placeholder only and contains no migration behavior.
"""

from __future__ import annotations

from ..contracts import ExecutionContext, ExecutionReport, PipelineStep


class DiscoverArchivesStep(PipelineStep):
    """Placeholder step for discovering source archives."""

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare archive discovery for the current migration context."""

        raise NotImplementedError

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute archive discovery for the current migration context."""

        raise NotImplementedError

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize archive discovery after execution."""

        raise NotImplementedError

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback archive discovery after failure."""

        raise NotImplementedError


__all__: list[str] = ["DiscoverArchivesStep"]
