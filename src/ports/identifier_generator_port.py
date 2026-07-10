"""Identifier generator port."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IdentifierGeneratorPort(ABC):
    """Abstract interface for generating domain identifiers."""

    @abstractmethod
    def next_archive_id(self) -> str:
        """Generate a new archive identifier."""

    @abstractmethod
    def next_mail_item_id(self) -> str:
        """Generate a new mail item identifier."""

    @abstractmethod
    def next_attachment_id(self) -> str:
        """Generate a new attachment identifier."""

    @abstractmethod
    def next_archived_file_id(self) -> str:
        """Generate a new archived file identifier."""

    @abstractmethod
    def next_job_id(self) -> str:
        """Generate a new migration job identifier."""

    @abstractmethod
    def next_migration_item_id(self) -> str:
        """Generate a new migration item identifier."""


__all__: list[str] = ["IdentifierGeneratorPort"]
