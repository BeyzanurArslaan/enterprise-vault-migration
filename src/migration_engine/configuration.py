"""Migration configuration module for the migration engine foundation.

This module defines the immutable configuration container for migration
execution settings. The configuration remains target-neutral and carries only
orchestration flags that influence how the pipeline behaves. The ``dry_run``
flag enables analysis-only execution without mutating the target system, and
the optional archive, folder, and date filters narrow the source scope without
introducing business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class MigrationConfiguration:
    """Immutable configuration object for migration engine settings."""

    dry_run: bool = False
    archive_names: tuple[str, ...] | None = None
    folder_paths: tuple[str, ...] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


__all__: list[str] = ["MigrationConfiguration"]
