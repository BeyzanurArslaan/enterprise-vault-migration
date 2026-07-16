"""Database adapters package for the migration platform.

This package groups repository implementations that back application and
engine persistence boundaries during development and testing.
"""

from __future__ import annotations

from .in_memory_checkpoint_repository import InMemoryCheckpointRepository
from .in_memory_retry_repository import InMemoryRetryRepository

__all__: list[str] = ["InMemoryCheckpointRepository", "InMemoryRetryRepository"]
