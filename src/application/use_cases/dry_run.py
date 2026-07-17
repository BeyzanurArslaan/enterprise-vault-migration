"""Dry run use case.

This module defines the application workflow for simulating a migration run
without mutating the target system. The use case reuses the existing pipeline
and forces ``dry_run=True`` on the runtime configuration while preserving the
rest of the execution context, including filters, checkpoints, retry
settings, and reporting metadata.
"""

from __future__ import annotations

from dataclasses import replace

from migration_engine.execution_result import ExecutionResult
from migration_engine.orchestrator import MigrationOrchestrator
from migration_engine.step_context import MigrationStepContext


class DryRunMigrationUseCase:
    """Coordinate a target-neutral dry-run migration execution."""

    def __init__(
        self,
        *,
        migration_orchestrator: MigrationOrchestrator,
    ) -> None:
        """Create a dry-run workflow bound to the existing orchestrator."""

        self._migration_orchestrator = migration_orchestrator

    def execute(
        self,
        *,
        initial_context: MigrationStepContext | None = None,
    ) -> ExecutionResult:
        """Execute the migration pipeline in analysis-only mode."""

        runner = self._migration_orchestrator.runner
        runtime_context = initial_context or runner.initial_context
        if runtime_context is None:
            message = "Dry-run execution requires an initial migration context."
            raise ValueError(message)

        dry_run_configuration = replace(
            runtime_context.execution_context.configuration,
            dry_run=True,
        )
        dry_run_execution_context = replace(
            runtime_context.execution_context,
            configuration=dry_run_configuration,
        )
        dry_run_context = replace(
            runtime_context,
            execution_context=dry_run_execution_context,
        )

        previous_initial_context = runner.initial_context
        runner.initial_context = dry_run_context
        try:
            return self._migration_orchestrator.run()
        finally:
            runner.initial_context = previous_initial_context


__all__: list[str] = ["DryRunMigrationUseCase"]
