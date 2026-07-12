"""Migration engine extraction package.

This package groups the immutable extraction result model used by the
migration engine's extract step.
"""

from __future__ import annotations

from .extraction_result import ExtractionResult

__all__: list[str] = ["ExtractionResult"]
