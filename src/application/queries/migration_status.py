"""Immutable migration status query.

This module defines the application contract for retrieving the status of a
migration workflow.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import MigrationJobId


@dataclass(slots=True, frozen=True)
class MigrationStatusQuery:
    """Immutable query for inspecting the current status of a migration."""

    job_id: MigrationJobId


__all__: list[str] = ["MigrationStatusQuery"]
