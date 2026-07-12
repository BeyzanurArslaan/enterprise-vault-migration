"""Metadata service module for the mock storionX subsystem.

This module defines a placeholder metadata service for the mock storionX
target platform scaffold. The service only declares metadata-oriented method
signatures and descriptive docstrings so the package structure is available
during development and testing without introducing behavior, persistence, or
infrastructure concerns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mock_storionx.entities import Document, Metadata, Workspace


class MetadataService(ABC):
    """Declare placeholder metadata operations for the mock storionX target."""

    @abstractmethod
    def create_metadata(
        self,
        *,
        document: Document,
        metadata: Metadata,
    ) -> Metadata:
        """Define a metadata creation operation for a document."""
        ...

    @abstractmethod
    def update_metadata(
        self,
        *,
        document: Document,
        metadata: Metadata,
    ) -> Metadata:
        """Define a metadata update operation for a document."""
        ...

    @abstractmethod
    def get_metadata(self, *, document: Document) -> Metadata:
        """Define a metadata retrieval operation for a document."""
        ...

    @abstractmethod
    def delete_metadata(self, *, document: Document) -> None:
        """Define a metadata deletion operation for a document."""
        ...

    @abstractmethod
    def list_metadata(self, *, workspace: Workspace | None = None) -> list[Metadata]:
        """Define a metadata listing operation, optionally scoped to a workspace."""
        ...


__all__: list[str] = ["MetadataService"]
