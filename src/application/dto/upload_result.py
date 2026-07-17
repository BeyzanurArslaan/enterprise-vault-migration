"""Immutable upload result DTO.

This module defines the application contract for the result of an upload step.
The ``idempotent_replay`` flag distinguishes a repeated successful submission
from a newly created target document while keeping the DTO target-neutral.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import MigrationItemId


@dataclass(slots=True, frozen=True)
class UploadResult:
    """Immutable result payload for an upload operation.

    The ``idempotent_replay`` field is ``True`` when the target already holds a
    matching document for the stable source identity and checksum.
    """

    item_id: MigrationItemId
    success: bool
    target_identifier: str | None
    error_message: str | None
    idempotent_replay: bool = False


__all__: list[str] = ["UploadResult"]
