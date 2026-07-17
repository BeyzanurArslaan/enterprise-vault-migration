"""Upload service module for the mock storionX subsystem.

This module defines a lightweight in-memory upload workflow for the mock
storionX target platform scaffold. The implementation intentionally avoids
persistence, REST concerns, and business rules while exposing the basic
session lifecycle used during development and testing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from threading import RLock
from uuid import uuid4

from mock_storionx.entities import Document, UploadSession


class UploadService:
    """Coordinate a placeholder upload workflow for the mock storionX target."""

    def __init__(self) -> None:
        """Create an upload service with no active session."""

        self._active_session: UploadSession | None = None
        self._lock = RLock()

    def create_upload_session(
        self,
        *,
        workspace_id: str,
        session_id: str | None = None,
        started_at: datetime | None = None,
    ) -> UploadSession:
        """Create and store a new upload session for a workspace."""

        upload_session = UploadSession(
            id=session_id or str(uuid4()),
            workspace_id=workspace_id,
            started_at=started_at or datetime.now(tz=UTC),
            uploaded_documents=[],
        )
        with self._lock:
            self._active_session = upload_session
            return upload_session

    @property
    def active_session(self) -> UploadSession | None:
        """Return the current active upload session when one exists."""

        with self._lock:
            return self._active_session

    def upload_document(
        self,
        *,
        document: Document,
        session_id: str | None = None,
    ) -> UploadSession:
        """Attach a document to the active upload session."""

        with self._lock:
            upload_session = self._require_active_session()
            if session_id is not None and session_id != upload_session.id:
                upload_session = UploadSession(
                    id=session_id,
                    workspace_id=upload_session.workspace_id,
                    started_at=upload_session.started_at,
                    completed_at=upload_session.completed_at,
                    uploaded_documents=list(upload_session.uploaded_documents),
                )
                self._active_session = upload_session

            upload_session.uploaded_documents.append(document)
            return upload_session

    def finalize_upload(
        self,
        *,
        completed_at: datetime | None = None,
    ) -> UploadSession:
        """Mark the active upload session as completed."""

        with self._lock:
            upload_session = self._require_active_session()
            upload_session.completed_at = completed_at or datetime.now(tz=UTC)
            return upload_session

    def _require_active_session(self) -> UploadSession:
        """Return the active session or raise an error if none exists."""

        if self._active_session is None:
            msg = "No active upload session exists."
            raise RuntimeError(msg)

        return self._active_session


__all__: list[str] = ["UploadService"]
