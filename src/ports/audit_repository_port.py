"""Repository port for audit events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AuditRepositoryPort(ABC):
    """Abstract interface for persisting audit events."""

    @abstractmethod
    def save(self, audit_event: Any) -> None:
        """Persist an audit event."""

    @abstractmethod
    def list_for_job(self, job_id: str) -> list[Any]:
        """List audit events for a migration job."""


__all__: list[str] = ["AuditRepositoryPort"]
