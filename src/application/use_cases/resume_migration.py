"""Resume migration use case.

This module defines the application workflow for continuing a migration from
the latest persisted checkpoint without coupling the application layer to
checkpoint storage or target adapters. The use case validates the checkpoint
contract, then delegates execution back to the orchestration boundary.
"""

from __future__ import annotations

from application.commands import ResumeMigrationCommand
from application.services import CheckpointService
from domain.exceptions import (
    CheckpointNotFoundError,
    NonResumableCheckpointError,
    UnsupportedCheckpointVersionError,
)
from domain.value_objects.identifiers import MigrationJobId
from migration_engine.execution_result import ExecutionResult
from migration_engine.orchestrator import MigrationOrchestrator
from migration_engine.state_machine import MigrationState


class ResumeMigrationUseCase:
    """Coordinate the resumption of a migration execution."""

    def __init__(
        self,
        *,
        checkpoint_service: CheckpointService,
        migration_orchestrator: MigrationOrchestrator,
    ) -> None:
        """Create a resume workflow bound to application services."""

        self._checkpoint_service = checkpoint_service
        self._migration_orchestrator = migration_orchestrator

    def execute(self, command: ResumeMigrationCommand) -> ExecutionResult:
        """Resume a migration run from the latest persisted checkpoint."""

        checkpoint_key = self._resolve_checkpoint_key(command.job_id)
        checkpoint = self._checkpoint_service.load_checkpoint(checkpoint_key)
        if checkpoint is None:
            message = f"No checkpoint exists for migration job {checkpoint_key}"
            raise CheckpointNotFoundError(message)

        self._validate_checkpoint(
            checkpoint_key=checkpoint_key,
            checkpoint_job_id=checkpoint.migration_job_id,
        )
        self._validate_schema_version(checkpoint.version)
        self._validate_state(checkpoint.current_state, force=command.force)

        return self._migration_orchestrator.run(resume_checkpoint=checkpoint)

    def _resolve_checkpoint_key(self, job_id: MigrationJobId | str) -> str:
        """Return the persistence key used for checkpoint lookup."""

        if isinstance(job_id, MigrationJobId):
            return str(job_id.value)

        return job_id

    def _validate_checkpoint(self, *, checkpoint_key: str, checkpoint_job_id: str) -> None:
        """Ensure the loaded checkpoint belongs to the requested migration job."""

        if checkpoint_key != checkpoint_job_id:
            message = "Loaded checkpoint does not match the requested migration job."
            raise NonResumableCheckpointError(message)

    def _validate_schema_version(self, version: int) -> None:
        """Ensure the checkpoint schema version is supported by the engine."""

        if version != 1:
            message = f"Unsupported checkpoint schema version: {version}"
            raise UnsupportedCheckpointVersionError(message)

    def _validate_state(self, state_value: str, *, force: bool) -> None:
        """Ensure the checkpoint state can safely resume execution."""

        try:
            checkpoint_state = MigrationState(state_value)
        except ValueError as exc:
            message = f"Unsupported checkpoint state: {state_value}"
            raise NonResumableCheckpointError(message) from exc

        if checkpoint_state in {MigrationState.COMPLETED, MigrationState.CANCELLED}:
            if force:
                message = "Forced resume is not supported for terminal checkpoints in this release."
                raise NonResumableCheckpointError(message)

            message = f"Checkpoint state is not resumable: {checkpoint_state.value}"
            raise NonResumableCheckpointError(message)


__all__: list[str] = ["ResumeMigrationUseCase"]
