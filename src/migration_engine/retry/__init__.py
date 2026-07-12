"""Retry policy package for the migration engine.

This package exposes the immutable retry decision contract and the
deterministic retry policy used by the orchestration layer. The package does
not execute retries, sleep, or persist retry history.
"""

from __future__ import annotations

from .retry_decision import RetryDecision
from .retry_policy import RetryPolicy

__all__: list[str] = ["RetryDecision", "RetryPolicy"]
