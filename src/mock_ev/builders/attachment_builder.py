"""Attachment builder for the mock Enterprise Vault subsystem.

This module defines the builder responsible for configuring mock attachment
artifacts in a reusable manner.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from mock_ev.entities import Attachment


class AttachmentBuilder:
    """Build mock attachment entities from prepared metadata."""

    def build(
        self,
        *,
        filename: str | None = None,
        name: str | None = None,
        extension: str | None = None,
        mime_type: str | None = None,
        content_type: str | None = None,
        size_bytes: int | None = None,
        size: int | None = None,
        checksum: str | None = None,
    ) -> Attachment:
        """Construct an attachment from pre-generated values."""

        selected_filename = filename or name
        if selected_filename is None:
            raise ValueError("filename is required")

        selected_extension = extension or Path(selected_filename).suffix.lower().lstrip(".")
        selected_mime_type = mime_type or content_type or "application/octet-stream"
        selected_size = size_bytes if size_bytes is not None else size
        if selected_size is None:
            selected_size = 0
        selected_checksum = checksum
        if selected_checksum is None:
            selected_checksum = hashlib.sha256(
                f"{selected_filename}|{selected_extension}|{selected_mime_type}|{selected_size}".encode()
            ).hexdigest()

        return Attachment(
            filename=selected_filename,
            extension=selected_extension,
            mime_type=selected_mime_type,
            size_bytes=selected_size,
            checksum=selected_checksum,
        )


__all__: list[str] = ["AttachmentBuilder"]
