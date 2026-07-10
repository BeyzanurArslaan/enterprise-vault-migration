"""Immutable audit log query.

This module defines the application contract for retrieving audit trail data for
a migration workflow.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import MigrationJobId


@dataclass(slots=True, frozen=True)
class AuditLogQuery:
    """Immutable query for retrieving audit log information for a migration."""

    job_id: MigrationJobId


__all__: list[str] = ["AuditLogQuery"]
