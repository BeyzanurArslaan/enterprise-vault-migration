"""Service package for the mock storionX subsystem.

This package groups the service placeholders used by the target platform
scaffold.
"""

from __future__ import annotations

from .upload_service import UploadService

__all__: list[str] = [
    "UploadService",
    "upload_service",
    "search_service",
    "metadata_service",
]
