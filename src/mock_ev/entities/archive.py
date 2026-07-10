"""Archive entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated archive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .journal_archive import JournalArchive
    from .mailbox import Mailbox


@dataclass(slots=True, kw_only=True)
class Archive:
    """Structural representation of a mock Enterprise Vault archive."""

    name: str
    mailboxes: list[Mailbox] = field(default_factory=list)
    journal_archives: list[JournalArchive] = field(default_factory=list)


__all__: list[str] = ["Archive"]
