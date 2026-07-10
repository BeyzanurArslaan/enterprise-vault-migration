"""Repository port for retry records."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RetryRepositoryPort(ABC):
    """Abstract interface for persisting retry records."""

    @abstractmethod
    def save(self, retry_record: Any) -> None:
        """Persist a retry record."""

    @abstractmethod
    def list_for_job(self, job_id: str) -> list[Any]:
        """List retry records for a migration job."""


__all__: list[str] = ["RetryRepositoryPort"]
