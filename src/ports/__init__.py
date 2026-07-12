"""Ports package for the domain layer.

This package groups the abstract boundaries used by the migration engine and
its surrounding application layers.
"""

from __future__ import annotations

from .storionx_target_port import StorionXTargetPort

__all__: list[str] = ["StorionXTargetPort"]
