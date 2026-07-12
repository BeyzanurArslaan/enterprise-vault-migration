"""API package for the mock storionX subsystem.

This package groups the API placeholders used by the target platform scaffold.
"""

from __future__ import annotations

from .health_api import HealthAPI
from .metadata_api import MetadataAPI
from .search_api import SearchAPI
from .upload_api import UploadAPI

__all__: list[str] = [
    "HealthAPI",
    "MetadataAPI",
    "SearchAPI",
    "UploadAPI",
]
