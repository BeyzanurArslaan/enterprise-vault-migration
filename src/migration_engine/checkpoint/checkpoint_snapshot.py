"""Checkpoint snapshot contract module for the migration engine.

This module defines the immutable continuation data captured for checkpointing
without storing raw email content, attachments, credentials, services, or
adapter references. The snapshot intentionally contains only the minimal
serializable state required to resume orchestration in a later sprint. The
``dry_run`` flag and ``dry_run_items`` counter preserve analysis-only runs
without storing any target-side state, and the optional filter fields preserve
the selected archive, folder, and date scope for safe resume operations.
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
    version: int = 1


__all__: list[str] = ["CheckpointSnapshot"]
