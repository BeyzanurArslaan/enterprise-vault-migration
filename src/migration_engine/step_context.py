"""Migration step context module for the migration engine foundation.

This module defines the immutable runtime context that is shared between
pipeline steps. The context only aggregates existing engine contracts and
does not implement any migration behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import ExecutionContext, ExecutionReport, SourceVaultStore
from .discovery import ArchiveDiscoveryResult
from .execution_result import ExecutionResult
from .extraction import ExtractionResult
from .progress_tracker import ProgressTracker
from .state_machine import MigrationStateMachine
from .transformation import TransformationResult
from .upload import UploadBatchResult
from .verification import VerificationResult


@dataclass(slots=True, frozen=True, kw_only=True)
class MigrationStepContext:
    """Immutable shared runtime context for a migration pipeline step."""

    execution_context: ExecutionContext
    progress_tracker: ProgressTracker | None = None
    state_machine: MigrationStateMachine | None = None
    execution_report: ExecutionReport | None = None
    discovery_result: ArchiveDiscoveryResult | None = None
    vault_stores: tuple[SourceVaultStore, ...] | None = None
    extraction_result: ExtractionResult | None = None
    transformation_result: TransformationResult | None = None
    upload_result: UploadBatchResult | None = None
    verification_result: VerificationResult | None = None
    execution_result: ExecutionResult | None = None


__all__: list[str] = ["MigrationStepContext"]
