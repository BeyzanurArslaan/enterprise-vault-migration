"""Folder entity module for the mock storionX subsystem.

This module defines the folder model used by the mock storionX target
platform scaffold. The entity is a plain structural dataclass with no
business rules or external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .document import Document


@dataclass(slots=True, kw_only=True)
class Folder:
    """Structural representation of a mock storionX folder."""

    id: str
    name: str
    path: str
    parent: Folder | None = None
    subfolders: list[Folder] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)


__all__: list[str] = ["Folder"]
