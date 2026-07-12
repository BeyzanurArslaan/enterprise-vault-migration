"""Transformation result module for the migration engine foundation.

This module defines the immutable summary produced by the transformation step.
The model captures orchestration metadata and transformed target documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mock_storionx.entities import Document


@dataclass(slots=True, frozen=True, kw_only=True)
class TransformationResult:
    """Immutable summary of a transformation pipeline execution."""

    transformed_documents: tuple[Document, ...]
    skipped_items: int
    failed_items: int
    warnings: tuple[str, ...]
    started_at: datetime | None
    completed_at: datetime | None


__all__: list[str] = ["TransformationResult"]
