"""Archived file entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated archived file.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class ArchivedFile:
    """Structural representation of a mock archived file artifact."""

    path: str
    size_bytes: int


__all__: list[str] = ["ArchivedFile"]
