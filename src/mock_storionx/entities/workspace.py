"""Workspace entity module for the mock storionX subsystem.

This module defines the immutable workspace aggregate used by the mock
storionX target platform scaffold. The model intentionally contains no
behavior, validation, or infrastructure concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .folder import Folder


@dataclass(slots=True, kw_only=True)
class Workspace:
    """Structural representation of a mock storionX workspace."""

    id: str
    name: str
    description: str | None = None
    folders: list[Folder] = field(default_factory=list)


__all__: list[str] = ["Workspace"]
