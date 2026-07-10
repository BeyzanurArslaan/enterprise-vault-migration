"""Migration status domain enumerations.

This module defines the lifecycle states used during migration processing.
"""

from __future__ import annotations

from enum import StrEnum


class MigrationStatus(StrEnum):
    """Supported lifecycle states for migration items."""

    PENDING = "pending"
    DISCOVERED = "discovered"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    REHYDRATING = "rehydrating"
    REHYDRATED = "rehydrated"
    TRANSFORMING = "transforming"
    TRANSFORMED = "transformed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


__all__: list[str] = ["MigrationStatus"]
