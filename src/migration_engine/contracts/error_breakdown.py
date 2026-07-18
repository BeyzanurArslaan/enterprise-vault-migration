"""Structured execution error breakdown contract module.

This module defines the immutable audit entry used by the migration engine to
capture terminal failure details in a security-safe and export-friendly form.
The entry stores only stable identifiers, stage metadata, retryability, and
human-readable classification fields. It deliberately excludes raw exception
objects, stack traces, binary payloads, and target or source entity graphs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True, kw_only=True)
class ErrorBreakdownEntry:
    """Immutable audit entry describing one terminal migration failure."""

    source_identifier: str | None
    stage: str
    category: str
    code: str
    message: str
    retryable: bool
    attempt_count: int
    final_status: str
    archive_identifier: str | None = None
    item_type: str | None = None


__all__: list[str] = ["ErrorBreakdownEntry"]
