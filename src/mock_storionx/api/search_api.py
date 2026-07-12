"""Search API module for the mock storionX subsystem.

This module defines a lightweight façade for the mock storionX search
interface. The implementation intentionally avoids networking, persistence,
and business logic while preserving the shape used during development and
testing.
"""

from __future__ import annotations

from mock_storionx.entities import Document, Metadata


class SearchAPI:
    """Expose placeholder search operations for the mock storionX façade."""

    def search_documents(self, *, query: str) -> list[Document]:
        """Define a placeholder document search operation."""

        return []

    def search_metadata(self, *, query: str) -> list[Metadata]:
        """Define a placeholder metadata search operation."""

        return []


__all__: list[str] = ["SearchAPI"]
