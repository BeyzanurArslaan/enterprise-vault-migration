"""Migration item entity for the migration domain.

This module defines the unit of work used to track an individual item through
migration processing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..enums.item_type import ItemType
from ..enums.migration_status import MigrationStatus
from ..value_objects.identifiers import MigrationItemId
from .base import BaseEntity


@dataclass(slots=True, kw_only=True)
class MigrationItem(BaseEntity):
    """Immutable structural representation of a migration item."""

    id: MigrationItemId
    source_item_id: str
    item_type: ItemType
    status: MigrationStatus
    retry_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None


__all__: list[str] = ["MigrationItem"]
