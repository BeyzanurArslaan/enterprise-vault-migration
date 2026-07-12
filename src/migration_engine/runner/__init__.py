"""Migration engine runner package.

This package defines the execution layer responsible for coordinating pipeline
steps. The current sprint establishes the runner and registry skeletons only,
without implementing execution behavior.
"""

from __future__ import annotations

from .pipeline_runner import PipelineRunner
from .step_registry import StepRegistry

__all__: list[str] = ["PipelineRunner", "StepRegistry"]
