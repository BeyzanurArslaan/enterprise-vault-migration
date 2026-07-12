"""Extraction result module for the migration engine foundation.

This module defines the immutable summary produced by the extract step. The
model captures structural extraction output and no behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from mock_ev.entities import Archive, Attachment, Mailbox, MailItem


@dataclass(slots=True, frozen=True, kw_only=True)
class ExtractionResult:
    """Immutable summary of extracted Enterprise Vault content."""

    discovered_archives: tuple[Archive, ...]
    extracted_mailboxes: tuple[Mailbox, ...]
    extracted_mail_items: tuple[MailItem, ...]
    extracted_attachments: tuple[Attachment, ...]
    total_mailboxes: int
    total_items: int
    total_attachments: int


__all__: list[str] = ["ExtractionResult"]
