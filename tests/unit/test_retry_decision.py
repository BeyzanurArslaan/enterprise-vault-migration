"""Regression tests for the immutable retry decision contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from domain.enums.retry_strategy import RetryStrategy
from migration_engine.retry import RetryDecision


def test_retry_decision_is_immutable_and_has_expected_fields() -> None:
    """Retry decisions should be frozen dataclasses with a fixed contract."""

    decision = RetryDecision(
        should_retry=True,
        attempt_number=2,
        remaining_attempts=1,
        delay_seconds=4.0,
        strategy=RetryStrategy.FIXED_DELAY,
        reason="retryable failure",
    )

    assert [field.name for field in fields(decision)] == [
        "should_retry",
        "attempt_number",
        "remaining_attempts",
        "delay_seconds",
        "strategy",
        "reason",
    ]
    assert decision.reason == "retryable failure"

    with pytest.raises(FrozenInstanceError):
        decision.reason = "changed"  # type: ignore[misc]


def test_retry_decision_does_not_store_exception_objects() -> None:
    """Retry decisions should remain serializable and exception-free."""

    decision = RetryDecision(
        should_retry=False,
        attempt_number=1,
        remaining_attempts=0,
        delay_seconds=0.0,
        strategy=RetryStrategy.NONE,
        reason=None,
    )

    assert not hasattr(decision, "exception")
    assert not hasattr(decision, "traceback")
    assert decision.reason is None
