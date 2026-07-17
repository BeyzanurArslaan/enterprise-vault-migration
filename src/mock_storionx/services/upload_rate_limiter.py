"""Shared rate limiter for the mock storionX upload workflow.

This module provides an execution-scoped, thread-safe limiter that assigns
deterministic retry-after delays for upload bursts. The limiter does not sleep
or raise transport-specific exceptions itself; the target adapter converts the
returned delay into a mock 429 response so the migration engine can exercise
its retry path without knowing anything about HTTP.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock


@dataclass(slots=True)
class UploadRateLimiter:
    """Deterministically schedule upload capacity across concurrent workers."""

    requests_per_second: float | None = None
    clock: Callable[[], datetime] | None = None
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _next_available_at: datetime | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate the limiter configuration."""

        if self.requests_per_second is not None and self.requests_per_second <= 0.0:
            message = "requests_per_second must be greater than 0 when configured."
            raise ValueError(message)

    def acquire_delay_seconds(self) -> float:
        """Return the delay required before the next upload may proceed."""

        if self.requests_per_second is None:
            return 0.0

        interval_seconds = 1.0 / self.requests_per_second
        now = self._now()
        with self._lock:
            if self._next_available_at is None or now >= self._next_available_at:
                self._next_available_at = now + timedelta(seconds=interval_seconds)
                return 0.0

            retry_after_seconds = (self._next_available_at - now).total_seconds()
            self._next_available_at += timedelta(seconds=interval_seconds)
            return max(retry_after_seconds, 0.0)

    def _now(self) -> datetime:
        """Return the current timestamp for limiter decisions."""

        if self.clock is not None:
            return self.clock()

        return datetime.now(tz=UTC)


__all__: list[str] = ["UploadRateLimiter"]
