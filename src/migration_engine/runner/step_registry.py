"""Step registry module for the migration engine execution layer.

This module defines the ordered registry used by the runner to resolve the
configured pipeline steps in deterministic migration order. The registry keeps
registration order, rejects duplicate step types, and resolves the concrete
workflow without coupling to infrastructure or target implementations.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..contracts import PipelineStep

_STEP_ORDER: dict[str, int] = {
    "DiscoverArchivesStep": 0,
    "ExtractItemsStep": 1,
    "TransformItemsStep": 2,
    "UploadItemsStep": 3,
    "VerifyItemsStep": 4,
    "FinalizeMigrationStep": 5,
}


class StepRegistry:
    """Manage ordered pipeline steps for execution."""

    def __init__(self, steps: Sequence[PipelineStep] = ()) -> None:
        """Create a registry seeded with ordered pipeline steps."""

        self._steps: tuple[PipelineStep, ...] = ()
        for step in steps:
            self.register(step)

    def register(self, step: PipelineStep) -> None:
        """Register a pipeline step for later resolution."""

        if self._contains_step_type(step):
            message = f"Duplicate step registration is not allowed: {step.__class__.__name__}"
            raise ValueError(message)

        self._steps = self._steps + (step,)

    @property
    def steps(self) -> tuple[PipelineStep, ...]:
        """Return the registered steps in registration order."""

        return self._steps

    def resolve(self) -> tuple[PipelineStep, ...]:
        """Resolve the registered pipeline steps in execution order."""

        return tuple(
            step
            for _, step in sorted(
                enumerate(self._steps),
                key=lambda item: self._step_sort_key(item[0], item[1]),
            )
        )

    def index_of(self, step_name: str) -> int | None:
        """Return the resolved index for a registered step name."""

        for index, step in enumerate(self.resolve()):
            if step.__class__.__name__ == step_name:
                return index

        return None

    def clear(self) -> None:
        """Clear the registered pipeline steps."""

        self._steps = ()

    def _contains_step_type(self, step: PipelineStep) -> bool:
        """Determine whether a step type has already been registered."""

        return any(existing.__class__ is step.__class__ for existing in self._steps)

    def _step_sort_key(self, index: int, step: PipelineStep) -> tuple[int, int]:
        """Return a deterministic ordering key for a registered step."""

        return (_STEP_ORDER.get(step.__class__.__name__, len(_STEP_ORDER)), index)


__all__: list[str] = ["StepRegistry"]
