"""Retry decision contract for the migration engine.

This module defines the immutable output produced by retry policy evaluation.
The decision is intentionally side-effect free and serialization-friendly so
the engine can reason about retry eligibility without storing exceptions,
tracebacks, or infrastructure objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.enums.retry_strategy import RetryStrategy


@dataclass(slots=True, frozen=True, kw_only=True)
class RetryDecision:
    """Immutable retry evaluation result for a single failed attempt.

    The ``attempt_number`` field follows the project convention that ``1``
    represents the initial execution attempt. ``max_attempts`` therefore
    includes the initial attempt, and ``remaining_attempts`` counts the number
    of additional attempts still available after the current attempt.
    """

    should_retry: bool
    attempt_number: int
    remaining_attempts: int
    delay_seconds: float
    strategy: RetryStrategy
    reason: str | None


__all__: list[str] = ["RetryDecision"]
