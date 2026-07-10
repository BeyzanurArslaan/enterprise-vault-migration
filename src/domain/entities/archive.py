"""Archive entity for the Enterprise Vault domain.

This module defines the archive aggregate root used to represent a collection
of related migration content in a framework-independent manner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..enums.archive_type import ArchiveType
from ..value_objects.identifiers import ArchiveId
from .base import BaseEntity

if TYPE_CHECKING:
    from .archived_file import ArchivedFile
    from .mail_item import MailItem


@dataclass(slots=True, kw_only=True)
class Archive(BaseEntity):
    """Immutable structural representation of an Enterprise Vault archive."""

    id: ArchiveId
    name: str
    archive_type: ArchiveType
    mail_items: list[MailItem] = field(default_factory=list)
    archived_files: list[ArchivedFile] = field(default_factory=list)


__all__: list[str] = ["Archive"]
