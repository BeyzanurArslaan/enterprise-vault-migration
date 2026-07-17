"""Migration metrics module for the migration engine foundation.

This module defines the immutable metrics model used by the migration engine
foundation. The model captures structural execution metrics and no behavior.
The ``idempotent_replays`` counter records successful upload replays that
reused an existing target document instead of creating a new record. The
``dry_run_items`` counter records uploads that were intentionally skipped in
analysis-only execution mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class MigrationMetrics:
    """Immutable metrics summary for a migration engine execution."""

    duration_seconds: float
    throughput_items_per_second: float
    average_item_size: int
    processed_bytes: int
    estimated_remaining_seconds: float | None
    peak_memory_usage_mb: float | None
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    retried_items: int = 0
    idempotent_replays: int = 0
    dry_run_items: int = 0
    uploaded_items: int = 0
    verification_failures: int = 0
    total_bytes: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


__all__: list[str] = ["MigrationMetrics"]
