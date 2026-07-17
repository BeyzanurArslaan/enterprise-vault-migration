"""Transformed document contract module for the migration engine.

This module defines the immutable target-neutral representation produced by
the transformation step. The model carries enough information for the target
adapter to materialize mock storionX entities without coupling the engine to
the target implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from domain.enums.archive_type import ArchiveType
from domain.enums.item_type import ItemType


@dataclass(slots=True, frozen=True, kw_only=True)
class TransformedDocument:
    """Immutable target-neutral representation of a transformed mail item."""

    source_identifier: str
    archive_name: str
    subject: str
    filename: str
    content_type: str
    size_bytes: int
    checksum: str
    sender: str
    recipients: tuple[str, ...]
    cc_recipients: tuple[str, ...]
    bcc_recipients: tuple[str, ...]
    retention_policy: str
    department: str
    tags: tuple[str, ...]
    custom_properties: tuple[tuple[str, str], ...]
    attachment_filenames: tuple[str, ...]
    attachment_checksums: tuple[str, ...]
    attachment_sizes: tuple[int, ...]
    created_at: datetime
    modified_at: datetime
    archive_type: ArchiveType = field(default=ArchiveType.MAILBOX, compare=False)
    item_type: ItemType = field(default=ItemType.EMAIL, compare=False)
    mailbox_address: str | None = field(default=None, compare=False)
    folder_path: str | None = field(default=None, compare=False)
    source_path: str | None = field(default=None, compare=False)
    is_orphaned: bool = field(default=False, compare=False)
    original_owner_identifier: str | None = field(default=None, compare=False)
    owner_resolution_status: str = field(default="resolved", compare=False)
    legal_hold: bool = field(default=False, compare=False)
    legal_hold_policy_id: str | None = field(default=None, compare=False)
    journal_metadata: tuple[tuple[str, str], ...] = field(default=(), compare=False)


__all__: list[str] = ["TransformedDocument"]
