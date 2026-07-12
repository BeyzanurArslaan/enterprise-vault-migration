"""Archive discovery result module for the migration engine foundation.

This module defines the immutable discovery summary produced by the archive
discovery step. The model contains only structural discovery data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True, kw_only=True)
class ArchiveDiscoveryResult:
    """Immutable summary of discovered vault stores and archives."""

    vault_store_names: tuple[str, ...]
    archive_names: tuple[str, ...]
    vault_store_count: int
    archive_count: int


__all__: list[str] = ["ArchiveDiscoveryResult"]
