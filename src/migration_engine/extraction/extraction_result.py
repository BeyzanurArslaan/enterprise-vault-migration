"""Extraction result module for the migration engine foundation.

This module defines the immutable summary produced by the extract step. The
model captures structural extraction output and no behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import SourceArchive, SourceAttachment, SourceMailbox, SourceMailItem


@dataclass(slots=True, frozen=True, kw_only=True)
class ExtractionResult:
    """Immutable summary of extracted Enterprise Vault content."""

    discovered_archives: tuple[SourceArchive, ...]
    extracted_mailboxes: tuple[SourceMailbox, ...]
    extracted_mail_items: tuple[SourceMailItem, ...]
    extracted_attachments: tuple[SourceAttachment, ...]
    total_mailboxes: int
    total_items: int
    total_attachments: int


__all__: list[str] = ["ExtractionResult"]
