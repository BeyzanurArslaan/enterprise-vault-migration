"""Archived file entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated archived file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from domain.enums.item_type import ItemType

if TYPE_CHECKING:
    from .content_part import ContentPart
    from .retention_policy import RetentionPolicy
    from .shortcut import Shortcut


@dataclass(slots=True, kw_only=True)
class ArchivedFile:
    """Structural representation of a mock archived file artifact."""

    path: str
    size_bytes: int
    checksum: str | None = None
    file_name: str | None = None
    extension: str | None = None
    archived_at: datetime | None = None
    modified_at: datetime | None = None
    legal_hold: bool = False
    legal_hold_policy_id: str | None = None
    source_path: str | None = None
    item_type: ItemType = ItemType.FILE
    shortcut: Shortcut | None = None
    content_parts: list[ContentPart] = field(default_factory=list)
    retention_policy: RetentionPolicy | None = None


__all__: list[str] = ["ArchivedFile"]
