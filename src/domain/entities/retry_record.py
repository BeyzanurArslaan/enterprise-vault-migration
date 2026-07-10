"""Retry record entity for the migration domain.

This module defines a retry record used to track retry behavior for migration
items.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..enums.retry_strategy import RetryStrategy
from ..value_objects.identifiers import MigrationItemId, RetryRecordId
from .base import BaseEntity


@dataclass(slots=True, kw_only=True)
class RetryRecord(BaseEntity):
    """Immutable structural representation of a retry record."""

    id: RetryRecordId
    migration_item_id: MigrationItemId
    retry_strategy: RetryStrategy
    attempt_number: int


__all__: list[str] = ["RetryRecord"]
