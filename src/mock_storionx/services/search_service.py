"""Search service module for the mock storionX subsystem.

This module defines a lightweight placeholder search service for the mock
storionX target platform scaffold. The service exposes a small, deterministic
surface area for development and testing without introducing persistence,
networking, or business rules.
"""

from __future__ import annotations

from mock_storionx.entities import Document, Folder, Metadata, Workspace


class SearchService:
    """Expose placeholder search operations for the mock storionX target."""

    def search_documents(
        self,
        *,
        query: str,
        workspace: Workspace | None = None,
        folder: Folder | None = None,
    ) -> list[Document]:
        """Return an empty document result set for the supplied search criteria."""

        return []

    def search_by_metadata(self, *, metadata: Metadata) -> list[Document]:
        """Return an empty document result set for metadata-driven searches."""

        return []

    def search_by_workspace(self, *, workspace: Workspace) -> list[Document]:
        """Return an empty document result set for workspace-scoped searches."""

        return []

    def search_by_folder(self, *, folder: Folder) -> list[Document]:
        """Return an empty document result set for folder-scoped searches."""

        return []


__all__: list[str] = ["SearchService"]
