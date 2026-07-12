"""In-memory checkpoint repository adapter module.

This module provides a concrete in-memory implementation of the checkpoint
repository port for development and testing. The repository stores immutable
checkpoint snapshots directly in memory and keeps the persistence boundary free
of filesystem, database, and orchestration concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ports import CheckpointRepositoryPort

if TYPE_CHECKING:
    from migration_engine.checkpoint import CheckpointSnapshot


class InMemoryCheckpointRepository(CheckpointRepositoryPort):
    """Store checkpoint snapshots in an isolated in-memory dictionary."""

    __slots__ = ("_checkpoints",)

    def __init__(self) -> None:
        """Create an empty in-memory checkpoint repository."""

        self._checkpoints: dict[str, CheckpointSnapshot] = {}

    def save_checkpoint(self, checkpoint: CheckpointSnapshot) -> None:
        """Store or replace a checkpoint snapshot by migration job identifier."""

        self._checkpoints[checkpoint.migration_job_id] = checkpoint

    def load_checkpoint(self, migration_job_id: str) -> CheckpointSnapshot | None:
        """Return the checkpoint snapshot for a migration job when present."""

        return self._checkpoints.get(migration_job_id)

    def delete_checkpoint(self, migration_job_id: str) -> None:
        """Remove the checkpoint snapshot for a migration job when present."""

        self._checkpoints.pop(migration_job_id, None)

    def checkpoint_exists(self, migration_job_id: str) -> bool:
        """Return whether a checkpoint snapshot exists for a migration job."""

        return migration_job_id in self._checkpoints


__all__: list[str] = ["InMemoryCheckpointRepository"]
