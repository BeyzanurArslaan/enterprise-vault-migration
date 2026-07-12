"""Entity package for the mock storionX subsystem.

This package groups the structural models used to represent the target
platform during migration.
"""

from __future__ import annotations

from .document import Document
from .folder import Folder
from .metadata import Metadata
from .upload_session import UploadSession
from .workspace import Workspace

__all__: list[str] = [
    "Document",
    "Folder",
    "Metadata",
    "UploadSession",
    "Workspace",
]
