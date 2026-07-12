"""Migration state machine module for the migration engine foundation.

This module defines the migration execution state model used by the engine
foundation. The current sprint establishes the state transition contract only
and intentionally leaves all behavior unimplemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MigrationState(StrEnum):
    """Enumerate the lifecycle states of a migration execution."""

    CREATED = "created"
    INITIALIZING = "initializing"
    DISCOVERING = "discovering"
    EXTRACTING = "extracting"
    TRANSFORMING = "transforming"
    UPLOADING = "uploading"
    VERIFYING = "verifying"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass(slots=True, kw_only=True)
class MigrationStateMachine:
    """Placeholder state machine for the migration engine lifecycle."""

    current_state: MigrationState
    previous_state: MigrationState | None = None

    def transition_to(self, state: MigrationState) -> None:
        """Transition the state machine to a new lifecycle state."""

        raise NotImplementedError

    def can_transition(self, state: MigrationState) -> bool:
        """Determine whether the state machine can move to a new state."""

        raise NotImplementedError

    def reset(self) -> None:
        """Reset the state machine to its initial lifecycle state."""

        raise NotImplementedError


__all__: list[str] = ["MigrationState", "MigrationStateMachine"]
