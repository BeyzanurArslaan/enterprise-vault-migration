"""Immutable migration request DTO.

This module defines the application contract for an incoming migration request.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import ArchiveId


@dataclass(slots=True, frozen=True)
class MigrationRequest:
    """Immutable request payload for initiating a migration workflow."""

    job_name: str
    archive_id: ArchiveId
    dry_run: bool
    resume: bool
    batch_size: int
    filter_expression: str | None


__all__: list[str] = ["MigrationRequest"]
