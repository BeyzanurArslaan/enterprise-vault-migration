"""Migration engine discovery package.

This package groups the structural discovery models used by the migration
engine's archive discovery step.
"""

from __future__ import annotations

from .archive_discovery_result import ArchiveDiscoveryResult

__all__: list[str] = ["ArchiveDiscoveryResult"]
