"""Migration configuration module for the migration engine foundation.

This module defines the immutable configuration container for migration
execution settings. The configuration remains target-neutral and carries only
orchestration flags that influence how the pipeline behaves. The ``dry_run``
flag enables analysis-only execution without mutating the target system, and
the optional archive, folder, and date filters narrow the source scope without
introducing business logic. The upload worker and request-rate settings shape
bounded parallel upload behavior without leaking target-specific concerns into
the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.exceptions import ValidationError


@dataclass(slots=True, frozen=True)
class MigrationConfiguration:
    """Immutable configuration object for migration engine settings."""

    dry_run: bool = False
    archive_names: tuple[str, ...] | None = None
    folder_paths: tuple[str, ...] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    upload_worker_count: int = 1
    upload_requests_per_second: float | None = None

    def __post_init__(self) -> None:
        """Validate the orchestration-only configuration values."""

        if self.upload_worker_count < 1:
            message = "upload_worker_count must be greater than or equal to 1."
            raise ValidationError(message)

        if self.upload_requests_per_second is not None and self.upload_requests_per_second <= 0.0:
            message = "upload_requests_per_second must be greater than 0 when configured."
            raise ValidationError(message)


__all__: list[str] = ["MigrationConfiguration"]
