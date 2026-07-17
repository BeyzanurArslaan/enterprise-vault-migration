"""Migration metrics module for the migration engine foundation.

This module defines the immutable metrics model used by the migration engine
foundation. The model captures structural execution metrics and no behavior.
The ``idempotent_replays`` counter records successful upload replays that
reused an existing target document instead of creating a new record. The
``dry_run_items`` counter records uploads that were intentionally skipped in
analysis-only execution mode. The ``filtered_archives`` and ``filtered_items``
fields record source entities excluded by configured migration filters. The
``rehydrated_items``, ``rehydration_failures``, ``rehydrated_bytes``,
``sis_cache_hits``, and ``sis_cache_misses`` counters summarize SIS
rehydration and cache reuse without duplicating the richer rehydration result
model. The ``reconciled_items``, ``missing_items``, and ``checksum_mismatches``
counters summarize reconciliation outcomes without duplicating the richer
result model.
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
    filtered_archives: int = 0
    filtered_items: int = 0
    retried_items: int = 0
    idempotent_replays: int = 0
    dry_run_items: int = 0
    rehydrated_items: int = 0
    rehydration_failures: int = 0
    rehydrated_bytes: int = 0
    sis_cache_hits: int = 0
    sis_cache_misses: int = 0
    reconciled_items: int = 0
    missing_items: int = 0
    checksum_mismatches: int = 0
    uploaded_items: int = 0
    verification_failures: int = 0
    total_bytes: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


__all__: list[str] = ["MigrationMetrics"]
