"""Metadata entity module for the mock storionX subsystem.

This module defines the metadata model used by the mock storionX target
platform scaffold. The entity stays framework-independent and contains only
typed data attributes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, kw_only=True)
class Metadata:
    """Structural representation of document metadata in mock storionX."""

    author: str
    department: str
    retention_policy: str
    tags: list[str] = field(default_factory=list)
    custom_properties: dict[str, str] = field(default_factory=dict)


__all__: list[str] = ["Metadata"]
