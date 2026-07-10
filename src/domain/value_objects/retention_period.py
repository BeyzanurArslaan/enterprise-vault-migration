"""Retention period value objects for the domain layer.

This module defines immutable retention period wrappers used to express policy
lifetimes in days without coupling the domain to infrastructure concerns.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetentionPeriod:
    """Immutable wrapper for a retention period in days."""

    value: int


__all__: list[str] = ["RetentionPeriod"]
