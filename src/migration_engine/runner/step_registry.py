"""Step registry module for the migration engine execution layer.

This module defines the placeholder registry that will eventually expose the
pipeline steps in execution order. The current implementation contains only the
class structure and registry method signatures.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..contracts import PipelineStep


class StepRegistry:
    """Placeholder registry for managing ordered pipeline steps."""

    def __init__(self, steps: Sequence[PipelineStep] = ()) -> None:
        """Create a registry seeded with ordered pipeline steps."""

        self.steps: tuple[PipelineStep, ...] = tuple(steps)

    def register(self, step: PipelineStep) -> None:
        """Register a pipeline step for later resolution."""

        raise NotImplementedError

    def resolve(self) -> tuple[PipelineStep, ...]:
        """Resolve the registered pipeline steps in execution order."""

        raise NotImplementedError

    def clear(self) -> None:
        """Clear the registered pipeline steps."""

        raise NotImplementedError


__all__: list[str] = ["StepRegistry"]
