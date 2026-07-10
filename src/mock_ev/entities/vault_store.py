"""Vault store entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated vault store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .archive import Archive


@dataclass(slots=True, kw_only=True)
class VaultStore:
    """Immutable structural representation of a mock Enterprise Vault vault store."""

    name: str
    archives: list[Archive] = field(default_factory=list)


__all__: list[str] = ["VaultStore"]
