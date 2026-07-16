"""Repository port for retry records.

This module defines the persistence boundary for retry records used by the
migration engine retry execution flow. The port intentionally exposes only
minimal, serializable retry records and does not couple callers to storage
implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.entities.retry_record import RetryRecord


class RetryRepositoryPort(ABC):
    """Abstract interface for persisting retry records."""

    @abstractmethod
    def save(self, retry_record: RetryRecord) -> None:
        """Persist a retry record."""

    @abstractmethod
    def list_for_job(self, job_id: str) -> list[RetryRecord]:
        """List retry records for a migration job."""


__all__: list[str] = ["RetryRepositoryPort"]
