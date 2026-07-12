"""Migration metrics module for the migration engine foundation.

This module defines the immutable metrics model used by the migration engine
foundation. The class currently carries only typed data and no behavior.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MigrationMetrics:
    """Immutable metrics summary for a migration engine execution."""

    duration_seconds: float
    throughput_items_per_second: float
    average_item_size: int
    processed_bytes: int
    estimated_remaining_seconds: float | None
    peak_memory_usage_mb: float | None


__all__: list[str] = ["MigrationMetrics"]
