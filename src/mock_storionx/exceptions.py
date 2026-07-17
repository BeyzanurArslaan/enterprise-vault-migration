"""Mock storionX exception types.

This module defines the infrastructure-facing exceptions used by the mock
storionX target to simulate transport-level failures such as 429 Too Many
Requests and 503 Service Unavailable. The exceptions carry only the minimal
metadata required for deterministic retry behavior and do not expose any HTTP
client or server objects.
"""

from __future__ import annotations


class MockStorionXError(Exception):
    """Base exception for mock storionX target failures."""


class TooManyRequestsError(MockStorionXError):
    """Raised when the mock target rate limiter rejects a request."""

    status_code: int = 429

    def __init__(self, *, retry_after_seconds: float) -> None:
        """Create a throttling error with deterministic retry-after metadata."""

        self.retry_after_seconds = retry_after_seconds
        message = f"Too Many Requests; retry after {retry_after_seconds:.3f} seconds."
        super().__init__(message)


class ServiceUnavailableError(MockStorionXError):
    """Raised when the mock target simulates a temporary service outage."""

    status_code: int = 503

    def __init__(self, *, retry_after_seconds: float = 0.0) -> None:
        """Create a temporary availability error with optional retry-after metadata."""

        self.retry_after_seconds = retry_after_seconds
        message = "Service Unavailable"
        if retry_after_seconds > 0.0:
            message = f"{message}; retry after {retry_after_seconds:.3f} seconds."
        super().__init__(message)


__all__: list[str] = [
    "MockStorionXError",
    "ServiceUnavailableError",
    "TooManyRequestsError",
]
