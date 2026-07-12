"""Migration pipeline module for the migration engine foundation.

This module defines the immutable workflow descriptor used by the migration
engine to carry an ordered collection of pipeline steps. The pipeline keeps
workflow definition separate from step registration and execution.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .contracts import PipelineStep


@dataclass(slots=True, frozen=True, kw_only=True)
class MigrationPipeline:
    """Immutable ordered description of a migration workflow."""

    steps: tuple[PipelineStep, ...] = ()

    def __iter__(self) -> Iterator[PipelineStep]:
        """Iterate over the configured pipeline steps."""

        return iter(self.steps)

    @property
    def step_count(self) -> int:
        """Return the number of configured pipeline steps."""

        return len(self.steps)


__all__: list[str] = ["MigrationPipeline"]
