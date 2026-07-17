"""Reconciliation result contract module for the migration engine.

This module defines the immutable summary produced by the final reconciliation
stage. The model compares the filtered transformed migration scope with the
observed target outcome using stable source identifiers and checksum metadata
without exposing any mock storionX entities. Unexpected target items remain an
empty tuple unless a later sprint introduces a safe scoped read capability.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True, kw_only=True)
class ReconciliationResult:
    """Immutable summary of a migration reconciliation run."""

    expected_items: int
    uploaded_items: int
    verified_items: int
    idempotent_replays: int
    dry_run_items: int
    missing_items: tuple[str, ...]
    unexpected_items: tuple[str, ...]
    checksum_mismatches: tuple[str, ...]
    status: str
    is_reconciled: bool


__all__: list[str] = ["ReconciliationResult"]
