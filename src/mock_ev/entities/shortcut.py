"""Shortcut entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated shortcut.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, kw_only=True)
class Shortcut:
    """Structural representation of a mock shortcut reference."""

    target_path: str
    description: str
    shortcut_id: str = ""
    original_source_item_id: str = ""
    archive_id: str = ""
    original_path: str = ""
    created_at: datetime | None = None
    archived_content_reference: str | None = None
    status: str = "valid"


__all__: list[str] = ["Shortcut"]
