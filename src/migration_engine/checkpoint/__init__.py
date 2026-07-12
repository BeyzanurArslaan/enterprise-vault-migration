"""Checkpoint package for the migration engine.

This package contains the immutable runtime checkpoint snapshot used by the
migration engine to capture safe continuation data. The package deliberately
keeps checkpointing separate from persistence and resume behavior.
"""

from __future__ import annotations

from .checkpoint_snapshot import CheckpointSnapshot

__all__: list[str] = ["CheckpointSnapshot"]
