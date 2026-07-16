"""Base entity definitions for the domain layer.

This module defines a shared base type for domain entities without introducing
persistence, validation, or infrastructure concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(slots=True, kw_only=True)
class BaseEntity:
    """Common base class for domain entities."""

    id: object = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


__all__: list[str] = ["BaseEntity"]
