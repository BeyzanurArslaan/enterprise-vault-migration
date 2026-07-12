"""Storage package for the mock storionX subsystem.

This package groups the storage placeholders used by the target platform
scaffold.
"""

from __future__ import annotations

from .in_memory_storage import (
    DocumentStorage,
    FolderStorage,
    MetadataStorage,
    UploadSessionStorage,
    WorkspaceStorage,
)

__all__: list[str] = [
    "DocumentStorage",
    "FolderStorage",
    "MetadataStorage",
    "UploadSessionStorage",
    "WorkspaceStorage",
]
