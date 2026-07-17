"""Entity package for the mock Enterprise Vault subsystem.

This package groups the model objects used to describe a simulated Enterprise
Vault environment.
"""

from __future__ import annotations

from .archive import Archive
from .archived_file import ArchivedFile
from .attachment import Attachment
from .content_part import ContentPart
from .journal_archive import JournalArchive
from .mail_item import MailItem
from .mailbox import Mailbox
from .retention_policy import RetentionPolicy
from .shortcut import Shortcut
from .vault_store import VaultStore

__all__: list[str] = [
    "ArchivedFile",
    "Archive",
    "Attachment",
    "ContentPart",
    "JournalArchive",
    "MailItem",
    "Mailbox",
    "RetentionPolicy",
    "Shortcut",
    "VaultStore",
]
