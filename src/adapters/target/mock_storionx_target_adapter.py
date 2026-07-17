"""Mock storionX target adapter module.

This module implements the storionX target port by mapping target-neutral
migration documents to the mock storionX entities and storing them in the
existing in-memory mock target services. The adapter enforces single-process
idempotency by treating the transformed document's stable ``source_identifier``
as the idempotency key for the mock target scope. Replays that match the
existing checksum and metadata return a neutral replay result without creating
duplicate target records. Conflicting replays raise a domain-level conflict
error so the migration engine can surface the failure structurally. Production
persistence would need a unique constraint on the idempotency key.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from application.dto import UploadResult
from domain.enums.archive_type import ArchiveType
from domain.enums.item_type import ItemType
from domain.exceptions import IdempotencyConflictError
from domain.value_objects.identifiers import MigrationItemId
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
        self._uploaded_documents: dict[str, TransformedDocument] = {}

    def create_archive(self, archive_id: str) -> str:
        """Create a target archive identifier placeholder."""

        self._ensure_session()
        return archive_id

    def upload_mail_item(self, mail_item_id: str, payload: object) -> UploadResult:
        """Upload a transformed mail item into the mock storionX target."""

        return self.upload_archived_file(mail_item_id, payload)

    def upload_attachment(self, attachment_id: str, payload: object) -> UploadResult:
        """Upload a transformed attachment into the mock storionX target."""

        return self.upload_archived_file(attachment_id, payload)

    def upload_archived_file(self, archived_file_id: str, payload: object) -> UploadResult:
        """Upload a transformed archived file into the mock storionX target."""

        transformed_document = self._require_transformed_document(payload)
        stored_document = self._map_document(transformed_document)
        existing_document = self.document_storage.get(stored_document.id)
        if existing_document is not None:
            if existing_document != stored_document:
                message = (
                    "Idempotency conflict for key "
                    f"{stored_document.id!r}: existing checksum "
                    f"{existing_document.checksum!r} does not match "
                    f"received checksum {stored_document.checksum!r}."
                )
                raise IdempotencyConflictError(message)

            self._uploaded_documents[stored_document.id] = transformed_document
            return self._build_upload_result(
                transformed_document=transformed_document,
                target_identifier=stored_document.id,
                idempotent_replay=True,
            )

        self._ensure_session()
        self.document_storage.add(stored_document)
        self._uploaded_documents[stored_document.id] = transformed_document
        self.upload_service.upload_document(
            document=stored_document,
            session_id=self._active_session_id,
        )
        return self._build_upload_result(
            transformed_document=transformed_document,
            target_identifier=stored_document.id,
            idempotent_replay=False,
        )

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
            custom_properties=self._build_custom_properties(transformed_document),
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

    def _build_custom_properties(
        self,
        transformed_document: TransformedDocument,
    ) -> dict[str, str]:
        """Build metadata properties while preserving migration-specific context."""

        custom_properties = dict(transformed_document.custom_properties)
        if transformed_document.archive_type != ArchiveType.MAILBOX:
            custom_properties["archive_type"] = transformed_document.archive_type.value
        if transformed_document.item_type != ItemType.EMAIL:
            custom_properties["item_type"] = transformed_document.item_type.value
        if transformed_document.mailbox_address is None:
            custom_properties["mailbox_address"] = ""
        if transformed_document.folder_path is not None:
            custom_properties["folder_path"] = transformed_document.folder_path
        if transformed_document.source_path is not None:
            custom_properties["source_path"] = transformed_document.source_path
        if transformed_document.is_orphaned:
            custom_properties["is_orphaned"] = "true"
        if transformed_document.original_owner_identifier is not None:
            custom_properties["original_owner_identifier"] = (
                transformed_document.original_owner_identifier
            )
        if transformed_document.owner_resolution_status != "resolved":
            custom_properties["owner_resolution_status"] = (
                transformed_document.owner_resolution_status
            )
        if transformed_document.legal_hold:
            custom_properties["legal_hold"] = "true"
        if transformed_document.legal_hold_policy_id is not None:
            custom_properties["legal_hold_policy_id"] = transformed_document.legal_hold_policy_id
        if transformed_document.journal_metadata:
            custom_properties["journal_metadata"] = ";".join(
                f"{key}={value}" for key, value in transformed_document.journal_metadata
            )

        return custom_properties

    def _build_upload_result(
        self,
        *,
        transformed_document: TransformedDocument,
        target_identifier: str,
        idempotent_replay: bool,
    ) -> UploadResult:
        """Build a target-neutral result for an upload operation."""

        return UploadResult(
            item_id=MigrationItemId(
                value=uuid5(NAMESPACE_URL, transformed_document.source_identifier)
            ),
            success=True,
            target_identifier=target_identifier,
            error_message=None,
            idempotent_replay=idempotent_replay,
        )


__all__: list[str] = ["MockStorionXTargetAdapter"]
