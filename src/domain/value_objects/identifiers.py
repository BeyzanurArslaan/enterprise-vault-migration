"""Identifier value objects for the domain layer.

This module defines immutable identifier wrappers used to represent domain
entities without coupling the domain to infrastructure concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MigrationJobId:
    """Immutable identifier for a migration job."""

    value: UUID


@dataclass(frozen=True, slots=True)
class MigrationItemId:
    """Immutable identifier for a migration item."""

    value: UUID


@dataclass(frozen=True, slots=True)
class ArchiveId:
    """Immutable identifier for an archive."""

    value: UUID


@dataclass(frozen=True, slots=True)
class MailItemId:
    """Immutable identifier for a mail item."""

    value: UUID


@dataclass(frozen=True, slots=True)
class AttachmentId:
    """Immutable identifier for an attachment."""

    value: UUID


__all__: list[str] = [
    "MigrationJobId",
    "MigrationItemId",
    "ArchiveId",
    "MailItemId",
    "AttachmentId",
]
