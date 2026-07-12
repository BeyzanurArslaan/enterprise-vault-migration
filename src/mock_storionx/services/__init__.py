"""Service package for the mock storionX subsystem.

This package groups the service placeholders used by the target platform
scaffold.
"""

from __future__ import annotations

from .metadata_service import MetadataService
from .search_service import SearchService
from .upload_service import UploadService

__all__: list[str] = [
    "MetadataService",
    "SearchService",
    "UploadService",
    "upload_service",
    "search_service",
    "metadata_service",
]
