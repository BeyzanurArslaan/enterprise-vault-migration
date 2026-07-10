"""Attachment entity for the Enterprise Vault domain.

This module defines the attachment aggregate used to represent file-based
content associated with a mail item in the migration platform.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..value_objects.checksum import Checksum
from ..value_objects.file_size import FileSize
from ..value_objects.identifiers import AttachmentId
from .base import BaseEntity


@dataclass(slots=True, kw_only=True)
class Attachment(BaseEntity):
    """Immutable structural representation of an attachment."""

    id: AttachmentId
    filename: str
    mime_type: str
    file_size: FileSize
    checksum: Checksum


__all__: list[str] = ["Attachment"]
