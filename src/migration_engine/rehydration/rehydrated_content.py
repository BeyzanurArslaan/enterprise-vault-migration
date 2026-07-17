"""Rehydrated content result module for the migration engine.

This module defines the immutable neutral payload returned by the SIS
rehydration service. The result carries the validated source content bytes,
the exact ordered parts that were used to rebuild the payload, and the
timestamp envelope supplied by the orchestration layer. The model is
behavior-free and intentionally omits any persistence or target-specific
concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..contracts import SourceContentPart


@dataclass(slots=True, frozen=True, kw_only=True)
class RehydratedContent:
    """Immutable neutral representation of rehydrated SIS content."""

    source_identifier: str
    content_bytes: bytes
    content_parts: tuple[SourceContentPart, ...]
    checksum: str
    size_bytes: int
    started_at: datetime
    completed_at: datetime


__all__: list[str] = ["RehydratedContent"]
