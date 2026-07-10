"""Retention policy entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated retention
policy used by the mock dataset generators.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class RetentionPolicy:
    """Structural representation of a mock retention policy."""

    name: str
    retention_days: int
    classification: str


__all__: list[str] = ["RetentionPolicy"]
