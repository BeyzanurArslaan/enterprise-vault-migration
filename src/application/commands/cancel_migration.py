"""Immutable cancel migration command.

This module defines the application contract for cancelling a migration run.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import MigrationJobId


@dataclass(slots=True, frozen=True)
class CancelMigrationCommand:
    """Immutable command used to cancel a migration workflow."""

    job_id: MigrationJobId


__all__: list[str] = ["CancelMigrationCommand"]
