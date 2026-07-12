"""Target adapters package for the migration platform.

This package groups adapter implementations that translate target-neutral
migration contracts into concrete storionX target operations.
"""

from __future__ import annotations

from .mock_storionx_target_adapter import MockStorionXTargetAdapter

__all__: list[str] = ["MockStorionXTargetAdapter"]
