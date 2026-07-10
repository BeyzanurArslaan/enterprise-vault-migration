"""Archived file entity for the Enterprise Vault domain.

This module defines the archived file aggregate used to represent file-system
content captured by the migration platform.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..value_objects.checksum import Checksum
from ..value_objects.file_size import FileSize
from ..value_objects.identifiers import ArchiveId
from ..value_objects.retention_period import RetentionPeriod
from .base import BaseEntity


@dataclass(slots=True, kw_only=True)
class ArchivedFile(BaseEntity):
    """Immutable structural representation of an archived file."""

    id: ArchiveId
    path: str
    file_size: FileSize
    checksum: Checksum
    retention_policy: RetentionPeriod


__all__: list[str] = ["ArchivedFile"]
