"""Archive type domain enumerations.

This module defines the supported archive source categories for the migration
platform.
"""

from __future__ import annotations

from enum import StrEnum


class ArchiveType(StrEnum):
    """Supported archive source types."""

    MAILBOX = "mailbox"
    JOURNAL = "journal"
    FSA = "fsa"
    SHAREPOINT = "sharepoint"


__all__: list[str] = ["ArchiveType"]
