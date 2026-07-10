"""Repository port for checkpoints."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CheckpointRepositoryPort(ABC):
    """Abstract interface for persisting checkpoints."""

    @abstractmethod
    def save(self, checkpoint: Any) -> None:
        """Persist a checkpoint."""

    @abstractmethod
    def get_by_job_id(self, job_id: str) -> Any:
        """Retrieve the latest checkpoint for a migration job."""


__all__: list[str] = ["CheckpointRepositoryPort"]
