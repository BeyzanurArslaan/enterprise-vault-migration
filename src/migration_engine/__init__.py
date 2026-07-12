"""Migration engine package for the enterprise vault migration project.

This package provides the foundational architecture for orchestrating content
migration from Enterprise Vault to storionX. The current sprint establishes the
engine skeleton only, without any migration behavior, infrastructure, or
runtime orchestration logic.
"""

from __future__ import annotations

from .configuration import MigrationConfiguration
from .context import MigrationContext
from .contracts import ProgressSnapshot
from .execution_result import ExecutionResult
from .metrics import MigrationMetrics
from .orchestrator import MigrationOrchestrator
from .pipeline import MigrationPipeline
from .progress_tracker import ProgressTracker
from .runner import PipelineRunner, StepRegistry
from .state_machine import MigrationState, MigrationStateMachine

__all__: list[str] = [
    "ExecutionResult",
    "MigrationConfiguration",
    "MigrationContext",
    "MigrationMetrics",
    "MigrationOrchestrator",
    "MigrationPipeline",
    "PipelineRunner",
    "ProgressSnapshot",
    "MigrationState",
    "MigrationStateMachine",
    "ProgressTracker",
    "StepRegistry",
]
