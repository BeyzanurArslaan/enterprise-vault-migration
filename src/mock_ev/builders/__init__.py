"""Builder package for the mock Enterprise Vault subsystem.

This package groups the builder components used to assemble mock Enterprise
Vault datasets in a structured, composable manner.
"""

from __future__ import annotations

from .archive_builder import ArchiveBuilder
from .attachment_builder import AttachmentBuilder
from .enterprise_vault_builder import EnterpriseVaultBuilder
from .mail_dataset_builder import MailDatasetBuilder
from .mailbox_builder import MailboxBuilder

__all__: list[str] = [
    "ArchiveBuilder",
    "AttachmentBuilder",
    "EnterpriseVaultBuilder",
    "MailDatasetBuilder",
    "MailboxBuilder",
]
