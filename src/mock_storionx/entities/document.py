"""Document entity module for the mock storionX subsystem.

This module defines the document model used by the mock storionX target
platform scaffold. The entity captures the minimum metadata required to
represent migrated content without any persistence or processing logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .metadata import Metadata


@dataclass(slots=True, kw_only=True)
class Document:
    """Structural representation of a mock storionX document."""

    id: str
    filename: str
    content_type: str
    size: int
    checksum: str
    metadata: Metadata
    created_at: datetime
    modified_at: datetime


__all__: list[str] = ["Document"]
