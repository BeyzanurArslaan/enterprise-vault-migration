"""File size value objects for the domain layer.

This module defines immutable file size wrappers used to represent byte counts
without coupling the domain to infrastructure concerns.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FileSize:
    """Immutable wrapper for a file size in bytes."""

    value: int


__all__: list[str] = ["FileSize"]
