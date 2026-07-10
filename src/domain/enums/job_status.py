"""Job status domain enumerations.

This module defines the lifecycle states for migration jobs.
"""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """Supported states for migration jobs."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


__all__: list[str] = ["JobStatus"]
