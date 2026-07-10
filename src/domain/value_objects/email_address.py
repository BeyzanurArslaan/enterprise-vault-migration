"""Email address value objects for the domain layer.

This module defines immutable email address wrappers used to represent contact
and mailbox identifiers without coupling the domain to infrastructure concerns.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmailAddress:
    """Immutable wrapper for an email address string."""

    value: str


__all__: list[str] = ["EmailAddress"]
