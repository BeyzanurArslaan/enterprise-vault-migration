"""Migration pipeline step contract module.

This module defines the abstract base class used to describe individual steps
within the migration execution pipeline. The contract establishes the lifecycle
shape without implementing any migration behavior.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .execution_context import ExecutionContext
from .execution_report import ExecutionReport


class PipelineStep(ABC):
    """Abstract contract for a single executable migration pipeline step."""

    @abstractmethod
    def prepare(self, context: ExecutionContext) -> None:
        """Prepare the step for execution using the shared context."""

    @abstractmethod
    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute the step and return its execution report."""

    @abstractmethod
    def finalize(self, context: ExecutionContext) -> None:
        """Finalize the step after successful execution."""

    @abstractmethod
    def rollback(self, context: ExecutionContext) -> None:
        """Rollback the step after a failed execution."""


__all__: list[str] = ["PipelineStep"]
