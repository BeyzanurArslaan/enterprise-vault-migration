"""Logging port for the domain layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LoggerPort(ABC):
    """Abstract interface for emitting logs."""

    @abstractmethod
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Emit a debug log message."""

    @abstractmethod
    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Emit an informational log message."""

    @abstractmethod
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Emit a warning log message."""

    @abstractmethod
    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Emit an error log message."""


__all__: list[str] = ["LoggerPort"]
