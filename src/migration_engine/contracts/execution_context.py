"""Migration execution context contract module.

This module defines the immutable data structure that carries shared
information across a migration engine execution. The context contains only
state and intentionally exposes no methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from ..configuration import MigrationConfiguration
from ..metrics import MigrationMetrics
from ..state_machine import MigrationState

if TYPE_CHECKING:
    from ..progress_tracker import ProgressTracker


@dataclass(slots=True, frozen=True)
class ExecutionContext:
    """Immutable shared execution state for a migration pipeline run."""

    migration_id: str
    configuration: MigrationConfiguration
    started_at: datetime
    current_step: str | None
    metrics: MigrationMetrics | None = None
    progress_tracker: ProgressTracker | None = None
    state: MigrationState | None = None
    current_timestamp: datetime | None = None


__all__: list[str] = ["ExecutionContext"]
