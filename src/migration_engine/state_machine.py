"""Migration state machine module for the migration engine foundation.

This module defines the migration execution state model used by the engine
foundation together with a lightweight transition guard for orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    """Track and validate migration lifecycle transitions."""

    current_state: MigrationState
    previous_state: MigrationState | None = None
    _initial_state: MigrationState = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Record the initial lifecycle state for later reset."""

        self._initial_state = self.current_state

    def transition_to(self, state: MigrationState) -> None:
        """Transition the state machine to a new lifecycle state."""

        if not self.can_transition(state):
            message = f"Cannot transition from {self.current_state} to {state}"
            raise ValueError(message)

        self.previous_state = self.current_state
        self.current_state = state

    def can_transition(self, state: MigrationState) -> bool:
        """Determine whether the state machine can move to a new state."""

        terminal_states = {
            MigrationState.COMPLETED,
            MigrationState.FAILED,
            MigrationState.CANCELLED,
        }
        if self.current_state in terminal_states:
            return state == self.current_state

        return True

    def reset(self) -> None:
        """Reset the state machine to its initial lifecycle state."""

        self.current_state = self._initial_state
        self.previous_state = None


__all__: list[str] = ["MigrationState", "MigrationStateMachine"]
