"""Immutable resume migration command.

This module defines the application contract for resuming a paused migration.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import MigrationJobId


@dataclass(slots=True, frozen=True)
class ResumeMigrationCommand:
    """Immutable command used to resume a paused migration workflow."""

    job_id: MigrationJobId


__all__: list[str] = ["ResumeMigrationCommand"]
