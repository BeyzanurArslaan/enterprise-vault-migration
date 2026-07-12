"""Upload contracts package for the migration engine foundation.

This package defines immutable upload coordination results used by the
migration engine orchestration layer.
"""

from __future__ import annotations

from .upload_result import UploadBatchResult

__all__: list[str] = ["UploadBatchResult"]
