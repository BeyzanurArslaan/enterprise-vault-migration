"""Regression tests for the mock storionX upload rate limiter.

This module verifies the deterministic, execution-scoped limiter used by the
mock storionX target adapter to simulate bounded upload throughput and
retry-after behavior without introducing transport or sleep dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mock_storionx.services import UploadRateLimiter


def test_upload_rate_limiter_schedules_retry_after_delays_deterministically() -> None:
    """The limiter should return deterministic retry-after delays."""

    timestamps = iter(
        (
            datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            datetime(2026, 1, 1, 12, 0, tzinfo=UTC) + timedelta(seconds=1),
        ),
    )
    limiter = UploadRateLimiter(requests_per_second=2.0, clock=lambda: next(timestamps))

    assert limiter.acquire_delay_seconds() == 0.0
    assert limiter.acquire_delay_seconds() == pytest.approx(0.5)
    assert limiter.acquire_delay_seconds() == 0.0


def test_upload_rate_limiter_rejects_invalid_request_rate() -> None:
    """The limiter should reject invalid throughput configuration."""

    with pytest.raises(ValueError):
        UploadRateLimiter(requests_per_second=0.0)
