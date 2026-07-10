"""Item type domain enumerations.

This module defines the content categories that can be processed by the
migration platform.
"""

from __future__ import annotations

from enum import StrEnum


class ItemType(StrEnum):
    """Supported migration item categories."""

    EMAIL = "email"
    ATTACHMENT = "attachment"
    FILE = "file"
    FOLDER = "folder"
    JOURNAL = "journal"


__all__: list[str] = ["ItemType"]
