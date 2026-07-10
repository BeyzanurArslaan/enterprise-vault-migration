"""Configuration port for runtime settings."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ConfigurationPort(ABC):
    """Abstract interface for retrieving configuration values."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""

    @abstractmethod
    def get_required(self, key: str) -> Any:
        """Get a required configuration value by key."""


__all__: list[str] = ["ConfigurationPort"]
