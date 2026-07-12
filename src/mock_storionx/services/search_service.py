"""Search service module for the mock storionX subsystem.

This module defines a placeholder search service for the mock storionX target
platform scaffold. The service only declares search-oriented method signatures
and descriptive docstrings so the package shape is available during
development and testing without introducing behavior, persistence, or
infrastructure concerns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mock_storionx.entities import Document, Folder, Metadata, Workspace


class SearchService(ABC):
    """Declare placeholder search operations for the mock storionX target."""

    @abstractmethod
    def search_documents(
        self,
        *,
        query: str,
        workspace: Workspace | None = None,
        folder: Folder | None = None,
    ) -> list[Document]:
        """Define a document search operation over the mock storionX model."""
        ...

    @abstractmethod
    def search_by_metadata(self, *, metadata: Metadata) -> list[Document]:
        """Define a metadata-driven document search operation."""
        ...

    @abstractmethod
    def search_by_workspace(self, *, workspace: Workspace) -> list[Document]:
        """Define a workspace-scoped document search operation."""
        ...

    @abstractmethod
    def search_by_folder(self, *, folder: Folder) -> list[Document]:
        """Define a folder-scoped document search operation."""
        ...


__all__: list[str] = ["SearchService"]
