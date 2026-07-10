"""Source port for Enterprise Vault interactions.

This module defines the interface through which the domain layer can access
Enterprise Vault sources without coupling to infrastructure implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EnterpriseVaultSourcePort(ABC):
    """Abstract interface for discovering and loading Enterprise Vault data."""

    @abstractmethod
    def discover_archives(self) -> Any:
        """Discover available archives."""

    @abstractmethod
    def load_archive(self, archive_id: str) -> Any:
        """Load an archive by identifier."""

    @abstractmethod
    def stream_mail_items(self, archive_id: str) -> Any:
        """Stream mail items from an archive."""

    @abstractmethod
    def stream_archived_files(self, archive_id: str) -> Any:
        """Stream archived files from an archive."""

    @abstractmethod
    def stream_attachments(self, archive_id: str) -> Any:
        """Stream attachments from an archive."""


__all__: list[str] = ["EnterpriseVaultSourcePort"]
