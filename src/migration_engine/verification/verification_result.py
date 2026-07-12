"""Verification result module for the migration engine foundation.

This module defines the immutable summary produced by the verification step.
The model captures orchestration metadata together with stable identifiers for
verified and mismatched target documents without introducing persistence or
repair behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationResult:
    """Immutable summary of a verification pipeline execution."""

    verified_document_ids: tuple[str, ...]
    failed_document_ids: tuple[str, ...]
    missing_document_ids: tuple[str, ...]
    checksum_mismatches: tuple[str, ...]
    metadata_mismatches: tuple[str, ...]
    verified_count: int
    failed_count: int
    started_at: datetime | None
    completed_at: datetime | None
    warnings: tuple[str, ...]


__all__: list[str] = ["VerificationResult"]
