"""Target port for storionX interactions.

This module defines the target boundary used by the migration engine to
publish transformed documents and read them back for post-upload verification
without coupling the engine to mock storionX implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from migration_engine.transformation import TransformedDocument


class StorionXTargetPort(ABC):
    """Abstract interface for publishing and reading storionX content."""

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

    @abstractmethod
    def get_uploaded_document(self, document_id: str) -> TransformedDocument | None:
        """Return an uploaded document using a target-neutral contract."""


__all__: list[str] = ["StorionXTargetPort"]
