"""Checkpoint snapshot contract module for the migration engine.

This module defines the immutable continuation data captured for checkpointing
without storing raw email content, attachments, credentials, services, or
adapter references. The snapshot intentionally contains only the minimal
serializable state required to resume orchestration in a later sprint. The
``dry_run`` flag and ``dry_run_items`` counter preserve analysis-only runs
without storing any target-side state, and the optional filter and upload
coordination fields preserve the selected archive scope together with the
worker and rate-limiting settings needed for deterministic resume behavior.
The ``throttled_uploads``, ``retry_after_count``, ``temporary_failures``, and
``worker_utilization`` counters persist the upload orchestration state that is
needed to resume a throttled or parallelized run deterministically without
storing any raw documents or transport objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True, kw_only=True)
class CheckpointSnapshot:
    """Immutable continuation snapshot for a migration execution checkpoint."""

    checkpoint_id: str
    migration_job_id: str
    last_completed_step: str | None
    last_processed_item_id: str | None
    processed_items: int
    successful_items: int
    failed_items: int
    skipped_items: int
    filtered_archives: int = 0
    filtered_items: int = 0
    uploaded_items: int
    verification_failures: int
    current_state: str
    created_at: datetime
    updated_at: datetime
    dry_run: bool = False
    dry_run_items: int = 0
    archive_names: tuple[str, ...] | None = None
    folder_paths: tuple[str, ...] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    upload_worker_count: int = 1
    upload_requests_per_second: float | None = None
    throttled_uploads: int = 0
    retry_after_count: int = 0
    temporary_failures: int = 0
    worker_utilization: float = 0.0
    version: int = 1


__all__: list[str] = ["CheckpointSnapshot"]
