"""Transformed document contract module for the migration engine.

This module defines the immutable target-neutral representation produced by
the transformation step. The model carries enough information for the target
adapter to materialize mock storionX entities without coupling the engine to
the target implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True, kw_only=True)
class TransformedDocument:
    """Immutable target-neutral representation of a transformed mail item."""

    source_identifier: str
    archive_name: str
    mailbox_address: str
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


__all__: list[str] = ["TransformedDocument"]
