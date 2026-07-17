"""Archive entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated archive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from domain.enums.archive_type import ArchiveType

if TYPE_CHECKING:
    from .archived_file import ArchivedFile
    from .journal_archive import JournalArchive
    from .mailbox import Mailbox
    from .shortcut import Shortcut


@dataclass(slots=True, kw_only=True)
class Archive:
    """Structural representation of a mock Enterprise Vault archive."""

    name: str
    archive_type: ArchiveType = ArchiveType.MAILBOX
    is_orphaned: bool = False
    original_owner_identifier: str | None = None
    owner_resolution_status: str = "resolved"
    mailboxes: list[Mailbox] = field(default_factory=list)
    journal_archives: list[JournalArchive] = field(default_factory=list)
    archived_files: list[ArchivedFile] = field(default_factory=list)
    shortcuts: list[Shortcut] = field(default_factory=list)
    source_path: str | None = None


__all__: list[str] = ["Archive"]
