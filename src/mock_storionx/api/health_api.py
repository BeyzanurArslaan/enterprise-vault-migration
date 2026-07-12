"""Health API module for the mock storionX subsystem.

This module defines a lightweight health-check façade for the mock storionX
interface. The implementation intentionally returns a fixed placeholder
response without any networking or infrastructure concerns.
"""

from __future__ import annotations


class HealthAPI:
    """Expose a placeholder health check for the mock storionX façade."""

    def health_check(self) -> dict[str, str]:
        """Return the fixed placeholder health response."""

        return {"status": "ok"}


__all__: list[str] = ["HealthAPI"]
