"""Upload session entity module for the mock storionX subsystem.

This module defines the upload session model used by the mock storionX target
platform scaffold. The entity records the upload lifecycle and the documents
associated with a given workspace upload run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .document import Document


@dataclass(slots=True, kw_only=True)
class UploadSession:
    """Structural representation of a mock storionX upload session."""

    id: str
    workspace_id: str
    started_at: datetime
    completed_at: datetime | None = None
    uploaded_documents: list[Document] = field(default_factory=list)


__all__: list[str] = ["UploadSession"]
