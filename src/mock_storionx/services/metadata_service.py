"""Metadata service module for the mock storionX subsystem.

This module defines a lightweight placeholder metadata service for the mock
storionX target platform scaffold. The service exposes a compact, deterministic
surface area for development and testing without introducing persistence,
networking, or business rules.
"""

from __future__ import annotations

from mock_storionx.entities import Document, Metadata, Workspace


class MetadataService:
    """Expose placeholder metadata operations for the mock storionX target."""

    def create_metadata(
        self,
        *,
        document: Document,
        metadata: Metadata,
    ) -> Metadata:
        """Return the provided metadata for a placeholder create operation."""

        return metadata

    def update_metadata(
        self,
        *,
        document: Document,
        metadata: Metadata,
    ) -> Metadata:
        """Return the provided metadata for a placeholder update operation."""

        return metadata

    def get_metadata(self, *, document: Document) -> Metadata:
        """Return the document metadata for a placeholder retrieval operation."""

        return document.metadata

    def delete_metadata(self, *, document: Document) -> None:
        """Perform a placeholder metadata deletion operation."""

        return None

    def list_metadata(self, *, workspace: Workspace | None = None) -> list[Metadata]:
        """Return an empty metadata list for the supplied scope."""

        return []


__all__: list[str] = ["MetadataService"]
