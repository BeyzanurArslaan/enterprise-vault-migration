"""Immutable migration result DTO.

This module defines the application contract for the outcome of a migration run.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.enums.job_status import JobStatus
from domain.value_objects.identifiers import MigrationJobId


@dataclass(slots=True, frozen=True)
class MigrationResult:
    """Immutable summary of a migration execution result."""

    job_id: MigrationJobId
    status: JobStatus
    processed_items: int
    successful_items: int
    failed_items: int


__all__: list[str] = ["MigrationResult"]
