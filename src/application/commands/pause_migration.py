"""Immutable pause migration command.

This module defines the application contract for pausing a migration run.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import MigrationJobId


@dataclass(slots=True, frozen=True)
class PauseMigrationCommand:
    """Immutable command used to pause an active migration workflow."""

    job_id: MigrationJobId


__all__: list[str] = ["PauseMigrationCommand"]
