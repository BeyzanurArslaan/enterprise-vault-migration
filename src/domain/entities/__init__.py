"""Entity package for the domain layer.

This package exports the domain entities that are shared across application
and engine boundaries.
"""

from __future__ import annotations

from .retry_record import RetryRecord

__all__: list[str] = ["RetryRecord"]
