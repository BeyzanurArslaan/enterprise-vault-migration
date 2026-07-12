"""Pipeline runner module for the migration engine execution layer.

This module defines the placeholder runner that will eventually coordinate the
execution of ordered migration pipeline steps. The current implementation
contains only the class structure and lifecycle method signatures.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..context import MigrationContext
from ..contracts import ExecutionContext, ExecutionReport, PipelineStep
from ..pipeline import MigrationPipeline


class PipelineRunner:
    """Placeholder runner for coordinating migration pipeline execution."""

    def __init__(
        self,
        steps: Sequence[PipelineStep],
        *,
        pipeline: MigrationPipeline | None = None,
        context: MigrationContext | None = None,
    ) -> None:
        """Create a runner configured with ordered pipeline steps."""

        self.steps: tuple[PipelineStep, ...] = tuple(steps)
        self.pipeline = pipeline
        self.context = context
        self.execution_context: ExecutionContext | None = None

    def initialize(self) -> ExecutionContext:
        """Prepare the runner before pipeline execution begins."""

        raise NotImplementedError

    def run(self) -> ExecutionReport:
        """Execute the configured pipeline steps in order."""

        raise NotImplementedError

    def shutdown(self) -> None:
        """Release runner resources after pipeline execution completes."""

        raise NotImplementedError


__all__: list[str] = ["PipelineRunner"]
