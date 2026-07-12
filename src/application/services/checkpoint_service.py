"""Checkpoint service module for the application layer.

This module defines the application-facing coordination contract for
checkpoint save and load operations. The service deliberately delegates to the
checkpoint repository port and stores only minimal, serializable continuation
state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ports import CheckpointRepositoryPort

if TYPE_CHECKING:
    from migration_engine.checkpoint import CheckpointSnapshot


class CheckpointService:
    """Coordinate checkpoint operations through the repository port."""

    def __init__(self, *, checkpoint_repository: CheckpointRepositoryPort) -> None:
        """Create a checkpoint service backed by a repository port."""

        self._checkpoint_repository = checkpoint_repository

    def save_checkpoint(self, checkpoint: CheckpointSnapshot) -> None:
        """Persist a checkpoint snapshot through the repository port."""

        self._checkpoint_repository.save_checkpoint(checkpoint)

    def load_checkpoint(self, migration_job_id: str) -> CheckpointSnapshot | None:
        """Load a checkpoint snapshot through the repository port."""

        return self._checkpoint_repository.load_checkpoint(migration_job_id)

    def delete_checkpoint(self, migration_job_id: str) -> None:
        """Delete a checkpoint snapshot through the repository port."""

        self._checkpoint_repository.delete_checkpoint(migration_job_id)

    def checkpoint_exists(self, migration_job_id: str) -> bool:
        """Return whether a checkpoint snapshot exists for a migration job."""

        return self._checkpoint_repository.checkpoint_exists(migration_job_id)


__all__: list[str] = ["CheckpointService"]
