"""Retry strategy domain enumerations.

This module defines the supported retry policies for transient migration
failures.
"""

from __future__ import annotations

from enum import StrEnum


class RetryStrategy(StrEnum):
    """Supported retry policies."""

    NONE = "none"
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"


__all__: list[str] = ["RetryStrategy"]
