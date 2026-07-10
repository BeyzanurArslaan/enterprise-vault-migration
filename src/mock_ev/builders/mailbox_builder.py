"""Mailbox builder for the mock Enterprise Vault subsystem.

This module defines the builder responsible for configuring mock mailbox
artifacts in a reusable manner.
"""

from __future__ import annotations

from collections.abc import Sequence

from mock_ev.entities import Mailbox, MailItem


class MailboxBuilder:
    """Build mock mailbox entities from prepared mail items."""

    def build(self, *, address: str, mail_items: Sequence[MailItem] | None = None) -> Mailbox:
        """Construct a mailbox from already-built mail items."""

        return Mailbox(address=address, mail_items=list(mail_items or []))


__all__: list[str] = ["MailboxBuilder"]
