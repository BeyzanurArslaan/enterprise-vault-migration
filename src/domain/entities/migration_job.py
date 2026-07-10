"""Migration job entity for the migration domain.

This module defines the aggregate root for migration jobs used by the
migration engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from ..enums.job_status import JobStatus
from ..value_objects.identifiers import MigrationJobId
from .base import BaseEntity

if TYPE_CHECKING:
    from .archive import Archive
    from .migration_item import MigrationItem


@dataclass(slots=True, kw_only=True)
class MigrationJob(BaseEntity):
    """Immutable structural representation of a migration job."""

    id: MigrationJobId
    name: str
    status: JobStatus
    source_archive: "Archive"
    items: list["MigrationItem"] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


__all__: list[str] = ["MigrationJob"]
