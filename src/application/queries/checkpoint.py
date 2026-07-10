"""Immutable checkpoint query.

This module defines the application contract for retrieving checkpoint
information related to a migration run.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import MigrationJobId


@dataclass(slots=True, frozen=True)
class CheckpointQuery:
    """Immutable query for retrieving checkpoint information for a migration."""

    job_id: MigrationJobId


__all__: list[str] = ["CheckpointQuery"]
