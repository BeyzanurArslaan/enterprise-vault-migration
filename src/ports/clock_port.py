"""Clock port for time-related operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class ClockPort(ABC):
    """Abstract interface for retrieving the current time."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current datetime."""


__all__: list[str] = ["ClockPort"]
