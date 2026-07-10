"""Journal archive entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated journal archive.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class JournalArchive:
    """Structural representation of a mock journal archive."""

    name: str
    retention_days: int


__all__: list[str] = ["JournalArchive"]
