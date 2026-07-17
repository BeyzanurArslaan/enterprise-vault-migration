"""Journal archive entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated journal archive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from domain.enums.archive_type import ArchiveType

if TYPE_CHECKING:
    from .mail_item import MailItem


@dataclass(slots=True, kw_only=True)
class JournalArchive:
    """Structural representation of a mock journal archive."""

    name: str
    retention_days: int
    archive_type: ArchiveType = ArchiveType.JOURNAL
    mail_items: list[MailItem] = field(default_factory=list)
    original_owner_identifier: str | None = None
    owner_resolution_status: str = "not_applicable"


__all__: list[str] = ["JournalArchive"]
