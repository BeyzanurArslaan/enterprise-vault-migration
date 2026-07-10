"""Checksum value objects for the domain layer.

This module defines immutable checksum wrappers used to represent content
integrity values without coupling the domain to infrastructure concerns.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Checksum:
    """Immutable wrapper for a SHA-256 checksum string."""

    value: str


__all__: list[str] = ["Checksum"]
