"""Migration progress snapshot contract module.

This module defines the immutable progress view used to capture migration
execution status at a point in time. The snapshot contains only data and no
behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class ProgressSnapshot:
    """Immutable snapshot of current migration progress."""

    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    skipped_items: int
    current_archive: str | None
    current_mailbox: str | None
    current_item: str | None
    started_at: datetime
    last_updated: datetime


__all__: list[str] = ["ProgressSnapshot"]
