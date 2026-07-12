"""Regression tests for the mock storionX target adapter."""

from __future__ import annotations

from datetime import UTC, datetime

from adapters.target import MockStorionXTargetAdapter
from migration_engine.transformation import TransformedDocument
from mock_storionx.entities import Document, Metadata, UploadSession


def _build_transformed_document() -> TransformedDocument:
    """Create a sample transformed document for adapter tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return TransformedDocument(
        source_identifier="message-1",
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject="Quarterly Report",
        filename="Quarterly Report.eml",
        content_type="message/rfc822",
        size_bytes=2048,
        checksum="checksum-message-1",
        sender="alice@example.com",
        recipients=("bob@example.com",),
        cc_recipients=("carol@example.com",),
        bcc_recipients=(),
        retention_policy="Standard",
        department="Finance",
        tags=("Archive One", "alice@example.com", "conversation-1"),
        custom_properties=(("priority", "high"), ("internet_message_id", "message-1")),
        attachment_filenames=("attachment-1.pdf",),
        attachment_checksums=("checksum-attachment-1.pdf",),
        attachment_sizes=(512,),
        created_at=timestamp,
        modified_at=timestamp,
    )


def _build_expected_document() -> Document:
    """Create the mock storionX document expected from the adapter."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return Document(
        id="message-1",
        filename="Quarterly Report.eml",
        content_type="message/rfc822",
        size=2048,
        checksum="checksum-message-1",
        metadata=Metadata(
            author="alice@example.com",
            department="Finance",
            retention_policy="Standard",
            tags=["Archive One", "alice@example.com", "conversation-1"],
            custom_properties={
                "priority": "high",
                "internet_message_id": "message-1",
            },
        ),
        created_at=timestamp,
        modified_at=timestamp,
    )


def test_mock_storionx_target_adapter_maps_and_persists_documents() -> None:
    """The adapter should map neutral documents to mock storionX entities."""

    transformed_document = _build_transformed_document()
    adapter = MockStorionXTargetAdapter(
        workspace_id="workspace-1",
        session_id="session-1",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    stored_document = adapter.upload_archived_file(
        transformed_document.source_identifier,
        transformed_document,
    )

    assert stored_document == _build_expected_document()
    assert adapter.document_storage.list() == [stored_document]
    assert adapter.upload_service.active_session is not None
    active_session = adapter.upload_service.active_session
    assert active_session is not None
    assert active_session.uploaded_documents == [stored_document]

    finalized_session = adapter.finalize_job("job-1")

    assert isinstance(finalized_session, UploadSession)
    assert finalized_session.completed_at is not None


def test_mock_storionx_target_adapter_skips_duplicate_document_uploads() -> None:
    """The adapter should not create duplicate target documents within one run."""

    transformed_document = _build_transformed_document()
    adapter = MockStorionXTargetAdapter(
        workspace_id="workspace-1",
        session_id="session-1",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    first_document = adapter.upload_archived_file(
        transformed_document.source_identifier,
        transformed_document,
    )
    second_document = adapter.upload_archived_file(
        transformed_document.source_identifier,
        transformed_document,
    )

    assert first_document == second_document
    assert adapter.document_storage.list() == [first_document]
    assert adapter.upload_service.active_session is not None
    active_session = adapter.upload_service.active_session
    assert active_session is not None
    assert active_session.uploaded_documents == [first_document]


def test_mock_storionx_target_adapter_returns_target_neutral_documents() -> None:
    """The adapter should return target-neutral uploaded documents for verification."""

    transformed_document = _build_transformed_document()
    adapter = MockStorionXTargetAdapter(
        workspace_id="workspace-1",
        session_id="session-1",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    adapter.upload_archived_file(
        transformed_document.source_identifier,
        transformed_document,
    )
    uploaded_document = adapter.get_uploaded_document(transformed_document.source_identifier)

    assert uploaded_document == transformed_document
    assert isinstance(uploaded_document, TransformedDocument)
    assert adapter.document_storage.get(transformed_document.source_identifier) == (
        _build_expected_document()
    )
