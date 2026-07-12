"""Regression tests for deterministic retry policy evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest

from domain.enums.retry_strategy import RetryStrategy
from domain.exceptions import ValidationError
from migration_engine.retry import RetryPolicy


def test_retry_policy_none_strategy_never_retries() -> None:
    """The none strategy should never permit another attempt."""

    policy = RetryPolicy(strategy=RetryStrategy.NONE, max_attempts=3)

    decision = policy.decide(attempt_number=1, retryable=True, reason="transient")

    assert decision.should_retry is False
    assert decision.delay_seconds == 0.0
    assert decision.remaining_attempts == 2
    assert decision.strategy is RetryStrategy.NONE
    assert decision.reason == "transient"


def test_retry_policy_fixed_delay_is_constant() -> None:
    """The fixed-delay strategy should return the same delay on each retry."""

    policy = RetryPolicy(
        strategy=RetryStrategy.FIXED_DELAY,
        max_attempts=4,
        fixed_delay_seconds=7.5,
    )

    first_decision = policy.decide(attempt_number=1, retryable=True)
    second_decision = policy.decide(attempt_number=2, retryable=True)

    assert first_decision.should_retry is True
    assert second_decision.should_retry is True
    assert first_decision.delay_seconds == 7.5
    assert second_decision.delay_seconds == 7.5


def test_retry_policy_exponential_backoff_grows_and_caps() -> None:
    """The exponential strategy should grow deterministically and respect the cap."""

    policy = RetryPolicy(
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        max_attempts=5,
        initial_backoff_seconds=2.0,
        maximum_backoff_seconds=5.0,
        backoff_multiplier=2.0,
    )

    first_decision = policy.decide(attempt_number=1, retryable=True)
    second_decision = policy.decide(attempt_number=2, retryable=True)
    third_decision = policy.decide(attempt_number=3, retryable=True)

    assert first_decision.delay_seconds == 2.0
    assert second_decision.delay_seconds == 4.0
    assert third_decision.delay_seconds == 5.0
    assert third_decision.should_retry is True


def test_retry_policy_retryable_false_never_retries() -> None:
    """A non-retryable failure should never permit another attempt."""

    policy = RetryPolicy(
        strategy=RetryStrategy.FIXED_DELAY,
        max_attempts=3,
        fixed_delay_seconds=1.0,
    )

    decision = policy.decide(attempt_number=1, retryable=False, reason="fatal")

    assert decision.should_retry is False
    assert decision.delay_seconds == 0.0
    assert decision.reason == "fatal"


def test_retry_policy_max_attempt_boundary_is_respected() -> None:
    """The final allowed attempt should not permit another retry."""

    policy = RetryPolicy(
        strategy=RetryStrategy.FIXED_DELAY,
        max_attempts=3,
        fixed_delay_seconds=1.0,
    )

    decision = policy.decide(attempt_number=3, retryable=True)

    assert decision.should_retry is False
    assert decision.remaining_attempts == 0
    assert decision.delay_seconds == 0.0


def test_retry_policy_remaining_attempts_follow_initial_attempt_convention() -> None:
    """Attempt number one should be treated as the initial execution attempt."""

    policy = RetryPolicy(
        strategy=RetryStrategy.FIXED_DELAY,
        max_attempts=4,
        fixed_delay_seconds=1.0,
    )

    decision = policy.decide(attempt_number=1, retryable=True)

    assert decision.remaining_attempts == 3


def test_retry_policy_decisions_are_deterministic() -> None:
    """The same inputs should always produce the same retry decision."""

    policy = RetryPolicy(
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        max_attempts=4,
        initial_backoff_seconds=1.5,
        maximum_backoff_seconds=10.0,
        backoff_multiplier=3.0,
    )

    first_decision = policy.decide(attempt_number=2, retryable=True, reason="transient")
    second_decision = policy.decide(attempt_number=2, retryable=True, reason="transient")

    assert first_decision == second_decision


def test_retry_policy_reason_is_propagated() -> None:
    """The retry reason should be carried through without transformation."""

    policy = RetryPolicy(
        strategy=RetryStrategy.FIXED_DELAY,
        max_attempts=2,
        fixed_delay_seconds=1.0,
    )

    decision = policy.decide(attempt_number=1, retryable=True, reason="temporary outage")

    assert decision.reason == "temporary outage"


@pytest.mark.parametrize(
    (
        "strategy",
        "max_attempts",
        "fixed_delay_seconds",
        "initial_backoff_seconds",
        "maximum_backoff_seconds",
        "backoff_multiplier",
    ),
    [
        (RetryStrategy.FIXED_DELAY, 0, 1.0, 0.0, 0.0, 1.0),
        (RetryStrategy.FIXED_DELAY, 1, -1.0, 0.0, 0.0, 1.0),
        (RetryStrategy.EXPONENTIAL_BACKOFF, 1, 0.0, -1.0, 1.0, 2.0),
        (RetryStrategy.EXPONENTIAL_BACKOFF, 1, 0.0, 1.0, -1.0, 2.0),
        (RetryStrategy.EXPONENTIAL_BACKOFF, 1, 0.0, 1.0, 0.5, 0.5),
        (RetryStrategy.EXPONENTIAL_BACKOFF, 1, 0.0, 2.0, 1.0, 2.0),
    ],
)
def test_retry_policy_rejects_invalid_configuration(
    strategy: RetryStrategy,
    max_attempts: int,
    fixed_delay_seconds: float,
    initial_backoff_seconds: float,
    maximum_backoff_seconds: float,
    backoff_multiplier: float,
) -> None:
    """Invalid retry configuration should raise a validation error."""

    with pytest.raises(ValidationError):
        RetryPolicy(
            strategy=strategy,
            max_attempts=max_attempts,
            fixed_delay_seconds=fixed_delay_seconds,
            initial_backoff_seconds=initial_backoff_seconds,
            maximum_backoff_seconds=maximum_backoff_seconds,
            backoff_multiplier=backoff_multiplier,
        )


def test_retry_policy_rejects_invalid_attempt_numbers() -> None:
    """Attempt numbering should remain one-based and positive."""

    policy = RetryPolicy(strategy=RetryStrategy.NONE, max_attempts=1)

    with pytest.raises(ValidationError):
        policy.decide(attempt_number=0, retryable=True)


def test_retry_policy_does_not_import_runtime_infrastructure() -> None:
    """The retry policy should stay free of runtime infrastructure coupling."""

    source_text = (
        Path(__file__)
        .resolve()
        .parents[2]
        .joinpath("src/migration_engine/retry/retry_policy.py")
        .read_text()
    )

    for forbidden_marker in (
        "mock_ev",
        "mock_storionx",
        "time.sleep",
        "asyncio.sleep",
        "sleep(",
        "PipelineRunner",
        "RetryRepositoryPort",
        "RepositoryPort",
    ):
        assert forbidden_marker not in source_text


def test_retry_package_does_not_duplicate_retry_record() -> None:
    """The retry package should expose only policy contracts, not another record."""

    source_text = (
        Path(__file__)
        .resolve()
        .parents[2]
        .joinpath("src/migration_engine/retry/__init__.py")
        .read_text()
    )
    assert "class RetryRecord" not in source_text
    assert "RetryDecision" in source_text
    assert "RetryPolicy" in source_text
