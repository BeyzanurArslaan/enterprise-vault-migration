"""Immutable upload result DTO.

This module defines the application contract for the result of an upload step.
The ``idempotent_replay`` flag distinguishes a repeated successful submission
from a newly created target document while keeping the DTO target-neutral.
The ``dry_run`` flag marks an intentional skip that did not mutate the target
system and therefore must not be treated as a real upload or a replay.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import MigrationItemId


@dataclass(slots=True, frozen=True)
class UploadResult:
    """Immutable result payload for an upload operation.

    The ``idempotent_replay`` field is ``True`` when the target already holds a
    matching document for the stable source identity and checksum.
    The ``dry_run`` field is ``True`` when the upload was intentionally
    skipped because the execution ran in analysis-only mode.
    """

    item_id: MigrationItemId
    success: bool
    target_identifier: str | None
    error_message: str | None
    idempotent_replay: bool = False
    dry_run: bool = False


__all__: list[str] = ["UploadResult"]
