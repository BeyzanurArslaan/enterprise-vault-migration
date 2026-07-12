"""Mock Enterprise Vault source adapter module.

This module implements the Enterprise Vault source port by exposing a
deterministic in-memory hierarchy of mock Enterprise Vault entities. The
adapter keeps the migration engine isolated from mock source implementations
while allowing acceptance tests to exercise the real workflow end to end.
"""

from __future__ import annotations

from collections.abc import Sequence

from mock_ev.entities import Archive, ArchivedFile, Attachment, MailItem, VaultStore
from ports import EnterpriseVaultSourcePort


class MockEnterpriseVaultSourceAdapter(EnterpriseVaultSourcePort):
    """Adapt mock Enterprise Vault entities to the source port boundary."""

    def __init__(
        self,
        *,
        vault_stores: Sequence[VaultStore] = (),
    ) -> None:
        """Create a source adapter backed by a deterministic vault hierarchy."""

        self._vault_stores = tuple(vault_stores)

    def discover_archives(self) -> tuple[VaultStore, ...]:
        """Return the configured vault stores and their archives."""

        return self._vault_stores

    def load_archive(self, archive_id: str) -> Archive | None:
        """Return the first archive whose name matches the requested identifier."""

        for archive in self._iter_archives():
            if archive.name == archive_id:
                return archive

        return None

    def stream_mail_items(self, archive_id: str) -> tuple[MailItem, ...]:
        """Return all mail items contained in the requested archive."""

        archive = self.load_archive(archive_id)
        if archive is None:
            return ()

        return tuple(mail_item for mailbox in archive.mailboxes for mail_item in mailbox.mail_items)

    def stream_archived_files(self, archive_id: str) -> tuple[ArchivedFile, ...]:
        """Return deterministic archived-file views for the requested archive."""

        archive = self.load_archive(archive_id)
        if archive is None:
            return ()

        archived_files: list[ArchivedFile] = []
        for mailbox in archive.mailboxes:
            for mail_item in mailbox.mail_items:
                archived_files.append(
                    ArchivedFile(
                        path=f"{archive.name}/{mailbox.address}/{mail_item.subject}.eml",
                        size_bytes=mail_item.message_size,
                    ),
                )

        return tuple(archived_files)

    def stream_attachments(self, archive_id: str) -> tuple[Attachment, ...]:
        """Return all attachments contained in the requested archive."""

        archive = self.load_archive(archive_id)
        if archive is None:
            return ()

        return tuple(
            attachment
            for mailbox in archive.mailboxes
            for mail_item in mailbox.mail_items
            for attachment in mail_item.attachments
        )

    def _iter_archives(self) -> tuple[Archive, ...]:
        """Iterate over all archives across the configured vault stores."""

        return tuple(
            archive for vault_store in self._vault_stores for archive in vault_store.archives
        )


__all__: list[str] = ["MockEnterpriseVaultSourceAdapter"]
