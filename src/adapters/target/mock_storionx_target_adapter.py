"""Mock storionX target adapter module.

This module implements the storionX target port by mapping target-neutral
migration documents to the mock storionX entities and storing them in the
existing in-memory mock target services.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from migration_engine.transformation import TransformedDocument
from mock_storionx.entities import Document, Metadata, UploadSession
from mock_storionx.services import UploadService
from mock_storionx.storage import DocumentStorage
from ports import StorionXTargetPort


class MockStorionXTargetAdapter(StorionXTargetPort):
    """Adapt target-neutral upload calls to the mock storionX subsystem."""

    def __init__(
        self,
        *,
        workspace_id: str = "workspace-1",
        upload_service: UploadService | None = None,
        document_storage: DocumentStorage | None = None,
        session_id: str | None = None,
        started_at: datetime | None = None,
    ) -> None:
        """Create an adapter backed by the existing mock storionX services."""

        self.workspace_id = workspace_id
        self.upload_service = upload_service or UploadService()
        self.document_storage = document_storage or DocumentStorage()
        self.session_id = session_id
        self.started_at = started_at or datetime.now(tz=UTC)
        self._active_session_id: str | None = None
        self._uploaded_document_ids: set[str] = set()
        self._uploaded_documents: dict[str, TransformedDocument] = {}

    def create_archive(self, archive_id: str) -> str:
        """Create a target archive identifier placeholder."""

        self._ensure_session()
        return archive_id

    def upload_mail_item(self, mail_item_id: str, payload: object) -> Document:
        """Upload a transformed mail item into the mock storionX target."""

        return self.upload_archived_file(mail_item_id, payload)

    def upload_attachment(self, attachment_id: str, payload: object) -> Document:
        """Upload a transformed attachment into the mock storionX target."""

        return self.upload_archived_file(attachment_id, payload)

    def upload_archived_file(self, archived_file_id: str, payload: object) -> Document:
        """Upload a transformed archived file into the mock storionX target."""

        transformed_document = self._require_transformed_document(payload)
        stored_document = self._map_document(transformed_document)
        existing_document = self.document_storage.get(stored_document.id)
        if existing_document is not None:
            return existing_document

        self._ensure_session()
        self.document_storage.add(stored_document)
        self._uploaded_document_ids.add(stored_document.id)
        self._uploaded_documents[stored_document.id] = transformed_document
        self.upload_service.upload_document(
            document=stored_document,
            session_id=self._active_session_id,
        )
        return stored_document

    def get_uploaded_document(self, document_id: str) -> TransformedDocument | None:
        """Return an uploaded document using the target-neutral contract."""

        stored_document = self.document_storage.get(document_id)
        if stored_document is None:
            return None

        return self._uploaded_documents.get(document_id)

    def finalize_job(self, job_id: str) -> UploadSession | str:
        """Finalize the active upload session when one exists."""

        active_session = self.upload_service.active_session
        if active_session is None:
            return job_id

        return self.upload_service.finalize_upload(
            completed_at=active_session.started_at,
        )

    def _ensure_session(self) -> UploadSession:
        """Create the active upload session when it does not exist yet."""

        active_session = self.upload_service.active_session
        if active_session is not None:
            self._active_session_id = active_session.id
            return active_session

        upload_session = self.upload_service.create_upload_session(
            workspace_id=self.workspace_id,
            session_id=self.session_id or str(uuid4()),
            started_at=self.started_at,
        )
        self._active_session_id = upload_session.id
        return upload_session

    def _require_transformed_document(
        self,
        payload: object,
    ) -> TransformedDocument:
        """Validate and return the transformed document payload."""

        if isinstance(payload, TransformedDocument):
            return payload

        message = "MockStorionXTargetAdapter expects a TransformedDocument payload."
        raise TypeError(message)

    def _map_document(self, transformed_document: TransformedDocument) -> Document:
        """Map a target-neutral transformed document to a mock storionX document."""

        metadata = Metadata(
            author=transformed_document.sender,
            department=transformed_document.department,
            retention_policy=transformed_document.retention_policy,
            tags=list(transformed_document.tags),
            custom_properties=dict(transformed_document.custom_properties),
        )
        return Document(
            id=transformed_document.source_identifier,
            filename=transformed_document.filename,
            content_type=transformed_document.content_type,
            size=transformed_document.size_bytes,
            checksum=transformed_document.checksum,
            metadata=metadata,
            created_at=transformed_document.created_at,
            modified_at=transformed_document.modified_at,
        )


__all__: list[str] = ["MockStorionXTargetAdapter"]
