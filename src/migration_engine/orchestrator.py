"""Migration orchestrator module for the migration engine foundation.

This module defines the thin orchestration façade that delegates migration
execution to the concrete pipeline runner. The orchestrator keeps application
composition separate from workflow execution and does not implement migration
logic itself.
"""

from __future__ import annotations

from .checkpoint import CheckpointSnapshot
from .execution_result import ExecutionResult
from .pipeline import MigrationPipeline
from .runner import PipelineRunner, StepRegistry
from .step_context import MigrationStepContext


class MigrationOrchestrator:
    """Thin façade over the concrete migration pipeline runner."""

    def __init__(
        self,
        *,
        runner: PipelineRunner,
        step_registry: StepRegistry | None = None,
        initial_context: MigrationStepContext | None = None,
        pipeline: MigrationPipeline | None = None,
    ) -> None:
        """Create an orchestrator that delegates to an existing pipeline runner."""

        self.runner = runner
        if step_registry is not None:
            self.runner.step_registry = step_registry
            self.runner.steps = step_registry.resolve()
        if pipeline is not None:
            self.runner.pipeline = pipeline
        if initial_context is not None:
            self.runner.initial_context = initial_context

    def run(
        self,
        *,
        resume_checkpoint: CheckpointSnapshot | None = None,
    ) -> ExecutionResult:
        """Execute the configured migration workflow."""

        return self.runner.run(resume_checkpoint=resume_checkpoint)


__all__: list[str] = ["MigrationOrchestrator"]
