"""Checkpoint entity for the migration domain.

This module defines a checkpoint artifact used to track progress during a
migration job.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..value_objects.identifiers import CheckpointId, MigrationJobId
from .base import BaseEntity


@dataclass(slots=True, kw_only=True)
class Checkpoint(BaseEntity):
    """Immutable structural representation of a migration checkpoint."""

    id: CheckpointId
    job_id: MigrationJobId
    last_processed_item_id: str


__all__: list[str] = ["Checkpoint"]
