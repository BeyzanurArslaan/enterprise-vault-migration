"""Shortcut entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated shortcut.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class Shortcut:
    """Structural representation of a mock shortcut reference."""

    target_path: str
    description: str


__all__: list[str] = ["Shortcut"]
