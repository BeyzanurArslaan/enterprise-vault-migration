"""Migration context module for the migration engine foundation.

This module defines the placeholder execution context that will eventually
carry shared state across migration orchestration, pipeline execution, and
state transitions. The class is intentionally behavior-free.
"""

from __future__ import annotations


class MigrationContext:
    """Placeholder context for sharing migration execution state."""

    pass


__all__: list[str] = ["MigrationContext"]
