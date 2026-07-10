"""Archive builder for the mock Enterprise Vault subsystem.

This module defines the builder responsible for configuring mock archive
artifacts in a reusable manner.
"""

from __future__ import annotations

from collections.abc import Sequence

from mock_ev.entities import Archive, JournalArchive, Mailbox


class ArchiveBuilder:
    """Build mock archive entities from prepared mailbox objects."""

    def build(
        self,
        *,
        name: str,
        mailboxes: Sequence[Mailbox] | None = None,
        journal_archives: Sequence[JournalArchive] | None = None,
    ) -> Archive:
        """Construct an archive from already-built children."""

        return Archive(
            name=name,
            mailboxes=list(mailboxes or []),
            journal_archives=list(journal_archives or []),
        )


__all__: list[str] = ["ArchiveBuilder"]
