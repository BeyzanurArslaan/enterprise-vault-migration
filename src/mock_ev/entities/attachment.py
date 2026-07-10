"""Attachment entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated attachment
used by the mock dataset generators.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class Attachment:
    """Structural representation of a mock attachment attached to a mail item."""

    filename: str
    extension: str
    mime_type: str
    size_bytes: int
    checksum: str

    @property
    def name(self) -> str:
        """Return the attachment filename for compatibility with older code."""

        return self.filename

    @property
    def content_type(self) -> str:
        """Return the MIME type for compatibility with older code."""

        return self.mime_type


__all__: list[str] = ["Attachment"]
