"""Transformation result module for the migration engine foundation.

This module defines the immutable summary produced by the transformation step.
The model captures orchestration metadata and transformed target-neutral
documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .transformed_document import TransformedDocument


@dataclass(slots=True, frozen=True, kw_only=True)
class TransformationResult:
    """Immutable summary of a transformation pipeline execution."""

    transformed_documents: tuple[TransformedDocument, ...]
    skipped_items: int
    failed_items: int
    warnings: tuple[str, ...]
    started_at: datetime | None
    completed_at: datetime | None
    failed_item_identifiers: tuple[str, ...] = ()


__all__: list[str] = ["TransformationResult"]
