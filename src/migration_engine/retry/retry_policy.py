"""Retry policy for deterministic migration retry decisions.

This module defines the smallest policy layer required for retry planning in
the migration engine. The policy does not sleep, execute steps, or persist
retry records. It only evaluates whether another attempt is permitted and, if
so, calculates the next delay deterministically.

Attempt numbering follows the repository convention used throughout the retry
tests:

* ``attempt_number == 1`` represents the initial execution attempt.
* ``max_attempts`` includes the initial attempt.
* ``remaining_attempts`` counts the number of additional attempts still
  available after the current attempt.

Supported strategies:

* ``NONE`` never retries and always returns a zero delay.
* ``FIXED_DELAY`` returns the configured fixed delay for every retryable
  attempt.
* ``EXPONENTIAL_BACKOFF`` returns ``initial_backoff_seconds *
  backoff_multiplier ** (attempt_number - 1)`` capped by
  ``maximum_backoff_seconds``.

The exponential strategy deliberately omits jitter so that policy decisions
remain deterministic and straightforward to test.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.enums.retry_strategy import RetryStrategy
from domain.exceptions import ValidationError

from .retry_decision import RetryDecision


@dataclass(slots=True, frozen=True, kw_only=True)
class RetryPolicy:
    """Evaluate retry eligibility and delay using a deterministic strategy."""

    strategy: RetryStrategy
    max_attempts: int
    fixed_delay_seconds: float = 0.0
    initial_backoff_seconds: float = 0.0
    maximum_backoff_seconds: float = 0.0
    backoff_multiplier: float = 1.0

    def __post_init__(self) -> None:
        """Validate the retry configuration before the policy is used."""

        if self.max_attempts < 1:
            message = "max_attempts must be greater than or equal to 1."
            raise ValidationError(message)

        if self.fixed_delay_seconds < 0.0:
            message = "fixed_delay_seconds must be greater than or equal to 0."
            raise ValidationError(message)

        if self.initial_backoff_seconds < 0.0:
            message = "initial_backoff_seconds must be greater than or equal to 0."
            raise ValidationError(message)

        if self.maximum_backoff_seconds < 0.0:
            message = "maximum_backoff_seconds must be greater than or equal to 0."
            raise ValidationError(message)

        if self.backoff_multiplier < 1.0:
            message = "backoff_multiplier must be greater than or equal to 1."
            raise ValidationError(message)

        if (
            self.strategy is RetryStrategy.EXPONENTIAL_BACKOFF
            and self.maximum_backoff_seconds < self.initial_backoff_seconds
        ):
            message = (
                "maximum_backoff_seconds must be greater than or equal to "
                "initial_backoff_seconds for exponential backoff."
            )
            raise ValidationError(message)

    def decide(
        self,
        *,
        attempt_number: int,
        retryable: bool,
        reason: str | None = None,
    ) -> RetryDecision:
        """Return a deterministic retry decision for the given attempt.

        ``attempt_number`` identifies the attempt that just completed. An
        attempt number of ``1`` therefore refers to the initial execution.
        """

        if attempt_number < 1:
            message = "attempt_number must be greater than or equal to 1."
            raise ValidationError(message)

        remaining_attempts = max(self.max_attempts - attempt_number, 0)
        should_retry = (
            retryable
            and self.strategy is not RetryStrategy.NONE
            and attempt_number < self.max_attempts
        )
        delay_seconds = self._calculate_delay(attempt_number, should_retry)
        return RetryDecision(
            should_retry=should_retry,
            attempt_number=attempt_number,
            remaining_attempts=remaining_attempts,
            delay_seconds=delay_seconds,
            strategy=self.strategy,
            reason=reason,
        )

    def _calculate_delay(self, attempt_number: int, should_retry: bool) -> float:
        """Calculate the retry delay for the configured strategy."""

        if not should_retry:
            return 0.0

        if self.strategy is RetryStrategy.NONE:
            return 0.0

        if self.strategy is RetryStrategy.FIXED_DELAY:
            return self.fixed_delay_seconds

        if self.strategy is RetryStrategy.EXPONENTIAL_BACKOFF:
            delay_seconds = self.initial_backoff_seconds * (
                self.backoff_multiplier ** (attempt_number - 1)
            )
            return min(delay_seconds, self.maximum_backoff_seconds)

        message = f"Unsupported retry strategy: {self.strategy!s}"
        raise ValidationError(message)


__all__: list[str] = ["RetryPolicy"]
