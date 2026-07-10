"""Checksum calculator port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class ChecksumCalculatorPort(ABC):
    """Abstract interface for calculating checksums."""

    @abstractmethod
    def calculate(self, stream: BinaryIO) -> str:
        """Calculate a checksum for the provided content stream."""


__all__: list[str] = ["ChecksumCalculatorPort"]
