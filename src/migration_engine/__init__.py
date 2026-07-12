"""Migration engine package for the enterprise vault migration project.

This package provides the foundational architecture for orchestrating content
migration from Enterprise Vault to storionX. The current sprint establishes the
execution-layer orchestration without any migration behavior, infrastructure,
or persistence.
"""

from __future__ import annotations

from .configuration import MigrationConfiguration
from .context import MigrationContext
from .contracts import ProgressSnapshot
from .discovery import ArchiveDiscoveryResult
from .execution_result import ExecutionResult
from .extraction import ExtractionResult
from .metrics import MigrationMetrics
from .orchestrator import MigrationOrchestrator
from .pipeline import MigrationPipeline
from .progress_tracker import ProgressTracker
from .runner import PipelineRunner, StepRegistry
from .state_machine import MigrationState, MigrationStateMachine
from .step_context import MigrationStepContext
from .transformation import TransformationResult, TransformedDocument
from .upload import UploadBatchResult

__all__: list[str] = [
    "ExecutionResult",
    "ArchiveDiscoveryResult",
    "MigrationConfiguration",
    "MigrationContext",
    "MigrationMetrics",
    "MigrationOrchestrator",
    "MigrationPipeline",
    "PipelineRunner",
    "ExtractionResult",
    "MigrationStepContext",
    "ProgressSnapshot",
    "MigrationState",
    "MigrationStateMachine",
    "ProgressTracker",
    "TransformedDocument",
    "UploadBatchResult",
    "StepRegistry",
    "TransformationResult",
]
