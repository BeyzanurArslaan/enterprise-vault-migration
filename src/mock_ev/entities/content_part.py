"""Content part entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated SIS content
part used by the mock dataset generators and the rehydration pipeline tests.
The entity is intentionally minimal and stores only the content bytes together
with the stable reference metadata needed for deterministic validation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class ContentPart:
    """Structural representation of a mock SIS content part."""

    part_id: str
    data_ref: str
    data: bytes
    size_bytes: int
    sha256: str


__all__: list[str] = ["ContentPart"]
