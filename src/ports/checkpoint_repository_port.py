"""Repository port for checkpoints.

This module defines the abstract persistence boundary for migration
checkpoints. The port intentionally exposes only serializable, target-neutral
checkpoint snapshots and avoids persistence details such as filesystem paths,
database types, or adapter implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from migration_engine.checkpoint import CheckpointSnapshot


class CheckpointRepositoryPort(ABC):
    """Abstract interface for persisting migration checkpoints."""

    @abstractmethod
    def save_checkpoint(self, checkpoint: CheckpointSnapshot) -> None:
        """Persist a checkpoint snapshot."""

    @abstractmethod
    def load_checkpoint(self, migration_job_id: str) -> CheckpointSnapshot | None:
        """Load the latest checkpoint snapshot for a migration job."""

    @abstractmethod
    def delete_checkpoint(self, migration_job_id: str) -> None:
        """Delete the checkpoint snapshot for a migration job."""

    @abstractmethod
    def checkpoint_exists(self, migration_job_id: str) -> bool:
        """Return whether a checkpoint snapshot exists for a migration job."""

    def save(self, checkpoint: CheckpointSnapshot) -> None:
        """Backward-compatible alias for saving a checkpoint snapshot."""

        self.save_checkpoint(checkpoint)

    def get_by_job_id(self, job_id: str) -> CheckpointSnapshot | None:
        """Backward-compatible alias for loading a checkpoint snapshot."""

        return self.load_checkpoint(job_id)


__all__: list[str] = ["CheckpointRepositoryPort"]
