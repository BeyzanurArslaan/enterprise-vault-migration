"""Upload result module for the migration engine foundation.

This module defines the immutable aggregate produced by the upload step. The
model captures orchestration metadata and item-level upload outcomes without
introducing persistence or retry behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.dto import UploadResult

from ..transformation import TransformedDocument


@dataclass(slots=True, frozen=True, kw_only=True)
class UploadBatchResult:
    """Immutable summary of a batch upload pipeline execution."""

    uploaded_documents: tuple[TransformedDocument, ...]
    failed_documents: tuple[TransformedDocument, ...]
    skipped_documents: tuple[TransformedDocument, ...]
    uploaded_document_ids: tuple[str, ...]
    item_results: tuple[UploadResult, ...]
    started_at: datetime | None
    completed_at: datetime | None


__all__: list[str] = ["UploadBatchResult"]
