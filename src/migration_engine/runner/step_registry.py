"""Step registry module for the migration engine execution layer.

This module defines the ordered registry used by the runner to resolve the
configured pipeline steps in execution order.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..contracts import PipelineStep


class StepRegistry:
    """Manage ordered pipeline steps for execution."""

    def __init__(self, steps: Sequence[PipelineStep] = ()) -> None:
        """Create a registry seeded with ordered pipeline steps."""

        self.steps: tuple[PipelineStep, ...] = tuple(steps)

    def register(self, step: PipelineStep) -> None:
        """Register a pipeline step for later resolution."""

        self.steps = self.steps + (step,)

    def resolve(self) -> tuple[PipelineStep, ...]:
        """Resolve the registered pipeline steps in execution order."""

        return self.steps

    def clear(self) -> None:
        """Clear the registered pipeline steps."""

        self.steps = ()


__all__: list[str] = ["StepRegistry"]
