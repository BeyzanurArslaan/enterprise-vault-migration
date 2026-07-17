"""Regression tests for the reconciliation result contract.

This module verifies that the migration engine exposes a frozen, target-neutral
reconciliation summary without adding any behavioral or infrastructure
coupling.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from migration_engine.reconciliation import ReconciliationResult


def test_reconciliation_result_is_immutable_and_target_neutral() -> None:
    """The reconciliation result should remain a frozen summary object."""

    result = ReconciliationResult(
        expected_items=3,
        uploaded_items=2,
        verified_items=2,
        idempotent_replays=1,
        dry_run_items=0,
        missing_items=("message-3",),
        unexpected_items=(),
        checksum_mismatches=("message-2",),
        status="needs_review",
        is_reconciled=False,
    )

    assert result.expected_items == 3
    assert result.uploaded_items == 2
    assert result.verified_items == 2
    assert result.idempotent_replays == 1
    assert result.missing_items == ("message-3",)
    assert result.checksum_mismatches == ("message-2",)
    assert result.status == "needs_review"
    assert result.is_reconciled is False

    with pytest.raises(FrozenInstanceError):
        type(result).__setattr__(result, "status", "reconciled")
