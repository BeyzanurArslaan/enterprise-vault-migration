"""Metadata API module for the mock storionX subsystem.

This module defines a lightweight façade for the mock storionX metadata
interface. The implementation intentionally avoids networking, persistence,
and business logic while preserving the shape used during development and
testing.
"""

from __future__ import annotations

from mock_storionx.entities import Metadata


class MetadataAPI:
    """Expose placeholder metadata operations for the mock storionX façade."""

    def create_metadata(self, *, metadata: Metadata) -> Metadata:
        """Define a placeholder metadata creation operation."""

        return metadata

    def get_metadata(self, *, metadata_id: str) -> Metadata | None:
        """Define a placeholder metadata lookup operation."""

        return None

    def update_metadata(self, *, metadata: Metadata) -> Metadata:
        """Define a placeholder metadata update operation."""

        return metadata

    def delete_metadata(self, *, metadata_id: str) -> None:
        """Define a placeholder metadata deletion operation."""
        return None

    def list_metadata(self) -> list[Metadata]:
        """Define a placeholder metadata listing operation."""

        return []


__all__: list[str] = ["MetadataAPI"]
