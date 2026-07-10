"""Target port for storionX interactions.

This module defines the interface through which the domain layer can interact
with storionX without coupling to infrastructure implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorionXTargetPort(ABC):
    """Abstract interface for publishing migrated content to storionX."""

    @abstractmethod
    def create_archive(self, archive_id: str) -> Any:
        """Create an archive target in storionX."""

    @abstractmethod
    def upload_mail_item(self, mail_item_id: str, payload: Any) -> Any:
        """Upload a mail item to storionX."""

    @abstractmethod
    def upload_attachment(self, attachment_id: str, payload: Any) -> Any:
        """Upload an attachment to storionX."""

    @abstractmethod
    def upload_archived_file(self, archived_file_id: str, payload: Any) -> Any:
        """Upload an archived file to storionX."""

    @abstractmethod
    def finalize_job(self, job_id: str) -> Any:
        """Finalize a migration job in storionX."""


__all__: list[str] = ["StorionXTargetPort"]
