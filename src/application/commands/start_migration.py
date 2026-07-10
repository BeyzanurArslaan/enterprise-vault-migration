"""Immutable start migration command.

This module defines the application contract for starting a migration run.
"""

from __future__ import annotations

from dataclasses import dataclass

from application.dto.migration_request import MigrationRequest


@dataclass(slots=True, frozen=True)
class StartMigrationCommand:
    """Immutable command used to initiate a migration workflow."""

    request: MigrationRequest


__all__: list[str] = ["StartMigrationCommand"]
