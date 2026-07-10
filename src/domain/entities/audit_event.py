"""Audit event entity for the migration domain.

This module defines an audit event used to record notable happenings during
migration execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..value_objects.identifiers import AuditEventId, MigrationJobId
from .base import BaseEntity


@dataclass(slots=True, kw_only=True)
class AuditEvent(BaseEntity):
    """Immutable structural representation of an audit event."""

    id: AuditEventId
    job_id: MigrationJobId
    event_type: str
    message: str
    occurred_at: datetime


__all__: list[str] = ["AuditEvent"]
