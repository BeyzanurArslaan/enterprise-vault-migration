"""Upload API module for the mock storionX subsystem.

This module defines a lightweight façade for the mock storionX upload
interface. The implementation intentionally avoids networking, persistence,
and business logic while preserving the shape used during development and
testing.
"""

from __future__ import annotations

from mock_storionx.entities import Document


class UploadAPI:
    """Expose placeholder upload operations for the mock storionX façade."""

    def upload_document(self, *, document: Document, session_id: str | None = None) -> None:
        """Define a placeholder upload document operation."""
        return None

    def finalize_upload(self, *, session_id: str) -> None:
        """Define a placeholder upload finalization operation."""
        return None


__all__: list[str] = ["UploadAPI"]
