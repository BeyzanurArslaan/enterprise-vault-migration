"""Immutable assessment result DTO.

This module defines the application contract for archive assessment metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import ArchiveId


@dataclass(slots=True, frozen=True)
class AssessmentResult:
    """Immutable assessment summary for an archive before migration."""

    archive_id: ArchiveId
    total_items: int
    estimated_size_bytes: int
    estimated_duration_minutes: int


__all__: list[str] = ["AssessmentResult"]
