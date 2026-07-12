"""Transformation contracts package for the migration engine foundation.

This package defines structural transformation outputs used by the migration
engine orchestration layer.
"""

from __future__ import annotations

from .transformation_result import TransformationResult

__all__: list[str] = ["TransformationResult"]
