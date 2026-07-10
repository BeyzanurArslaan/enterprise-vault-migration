"""Immutable upload result DTO.

This module defines the application contract for the result of an upload step.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.identifiers import MigrationItemId


@dataclass(slots=True, frozen=True)
class UploadResult:
    """Immutable result payload for an upload operation."""

    item_id: MigrationItemId
    success: bool
    target_identifier: str | None
    error_message: str | None


__all__: list[str] = ["UploadResult"]
