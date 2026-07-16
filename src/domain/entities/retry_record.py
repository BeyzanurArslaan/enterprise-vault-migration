"""Retry record entity for the migration domain.

This module defines the immutable retry record used to track retry behavior
for both migration items and step-level orchestration retries. The record
stores only minimal identifiers and diagnostics so the domain layer stays free
of exception objects, tracebacks, and infrastructure dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..enums.retry_strategy import RetryStrategy
from ..value_objects.identifiers import MigrationItemId, RetryRecordId
from .base import BaseEntity


@dataclass(slots=True, kw_only=True)
class RetryRecord(BaseEntity):
    """Immutable structural representation of a retry record."""

    id: RetryRecordId
    migration_item_id: MigrationItemId | None
    retry_strategy: RetryStrategy
    attempt_number: int
    migration_job_id: str | None = None
    pipeline_step_name: str | None = None
    retry_reason: str | None = None


__all__: list[str] = ["RetryRecord"]
