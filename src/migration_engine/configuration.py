"""Migration configuration module for the migration engine foundation.

This module defines the immutable configuration container for migration
execution settings. The configuration remains target-neutral and carries only
orchestration flags that influence how the pipeline behaves. The ``dry_run``
flag enables analysis-only execution without mutating the target system.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MigrationConfiguration:
    """Immutable configuration object for migration engine settings."""

    dry_run: bool = False


__all__: list[str] = ["MigrationConfiguration"]
