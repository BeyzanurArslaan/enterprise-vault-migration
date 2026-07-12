"""Migration pipeline module for the migration engine foundation.

This module defines the placeholder pipeline abstraction that will later
compose migration stages into a deterministic execution flow. No pipeline
logic is implemented in this sprint.
"""

from __future__ import annotations


class MigrationPipeline:
    """Placeholder pipeline for assembling migration stages."""

    pass


__all__: list[str] = ["MigrationPipeline"]
