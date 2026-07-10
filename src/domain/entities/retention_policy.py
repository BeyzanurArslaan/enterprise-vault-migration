"""Retention policy entity for the migration domain.

This module defines the retention policy used to describe the lifecycle of
migrated content.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..value_objects.identifiers import RetentionPolicyId
from ..value_objects.retention_period import RetentionPeriod
from .base import BaseEntity


@dataclass(slots=True, kw_only=True)
class RetentionPolicy(BaseEntity):
    """Immutable structural representation of a retention policy."""

    id: RetentionPolicyId
    name: str
    retention_period: RetentionPeriod


__all__: list[str] = ["RetentionPolicy"]
