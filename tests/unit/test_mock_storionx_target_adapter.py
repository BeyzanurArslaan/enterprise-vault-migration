"""Regression tests for the mock storionX target adapter."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from adapters.target import MockStorionXTargetAdapter
from domain.exceptions import IdempotencyConflictError
from migration_engine.transformation import TransformedDocument
from mock_storionx.entities import Document, Metadata, UploadSession
from mock_storionx.exceptions import ServiceUnavailableError, TooManyRequestsError
from mock_storionx.services import UploadRateLimiter


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

    upload_result = adapter.upload_archived_file(
        transformed_document.source_identifier,
        transformed_document,
    )

    stored_document = adapter.document_storage.get(transformed_document.source_identifier)
    assert stored_document is not None
    assert stored_document == _build_expected_document()
    assert upload_result.success is True
    assert upload_result.target_identifier == transformed_document.source_identifier
    assert upload_result.error_message is None
    assert upload_result.idempotent_replay is False
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

    first_upload = adapter.upload_archived_file(
        transformed_document.source_identifier,
        transformed_document,
    )
    second_upload = adapter.upload_archived_file(
        transformed_document.source_identifier,
        transformed_document,
    )

    assert first_upload.success is True
    assert first_upload.idempotent_replay is False
    assert second_upload.success is True
    assert second_upload.idempotent_replay is True
    assert first_upload.target_identifier == second_upload.target_identifier
    stored_document = adapter.document_storage.get(transformed_document.source_identifier)
    assert stored_document is not None
    assert stored_document == _build_expected_document()
    assert adapter.document_storage.list() == [stored_document]
    assert adapter.upload_service.active_session is not None
    active_session = adapter.upload_service.active_session
    assert active_session is not None
    assert active_session.uploaded_documents == [stored_document]


def test_mock_storionx_target_adapter_rejects_conflicting_replays() -> None:
    """The adapter should refuse to overwrite conflicting target content."""

    transformed_document = _build_transformed_document()
    conflicting_document = replace(transformed_document, checksum="different-checksum")
    adapter = MockStorionXTargetAdapter(
        workspace_id="workspace-1",
        session_id="session-1",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    adapter.upload_archived_file(
        transformed_document.source_identifier,
        transformed_document,
    )

    try:
        adapter.upload_archived_file(
            conflicting_document.source_identifier,
            conflicting_document,
        )
    except IdempotencyConflictError as exc:
        assert "Idempotency conflict" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected an idempotency conflict")
    stored_document = adapter.document_storage.get(transformed_document.source_identifier)
    assert stored_document is not None
    assert adapter.document_storage.list() == [stored_document]


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


def test_mock_storionx_target_adapter_raises_retry_after_for_throttled_uploads() -> None:
    """The adapter should surface retry-after metadata when rate limited."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    transformed_document = _build_transformed_document()
    adapter = MockStorionXTargetAdapter(
        workspace_id="workspace-1",
        session_id="session-1",
        started_at=timestamp,
        rate_limiter=UploadRateLimiter(
            requests_per_second=1.0,
            clock=lambda: timestamp,
        ),
    )

    first_result = adapter.upload_archived_file(
        transformed_document.source_identifier,
        transformed_document,
    )

    with pytest.raises(TooManyRequestsError) as exc_info:
        adapter.upload_archived_file(
            transformed_document.source_identifier,
            transformed_document,
        )

    assert first_result.success is True
    assert exc_info.value.retry_after_seconds == pytest.approx(1.0)
    assert adapter.document_storage.list() == [_build_expected_document()]


def test_mock_storionx_target_adapter_shares_limiter_across_instances() -> None:
    """The adapter should honor a shared limiter across worker-safe instances."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    shared_rate_limiter = UploadRateLimiter(
        requests_per_second=1.0,
        clock=lambda: timestamp,
    )
    first_adapter = MockStorionXTargetAdapter(
        workspace_id="workspace-1",
        session_id="session-1",
        started_at=timestamp,
        rate_limiter=shared_rate_limiter,
    )
    second_adapter = MockStorionXTargetAdapter(
        workspace_id="workspace-1",
        session_id="session-2",
        started_at=timestamp,
        rate_limiter=shared_rate_limiter,
    )

    first_result = first_adapter.upload_archived_file(
        "message-1",
        _build_transformed_document(),
    )

    with pytest.raises(TooManyRequestsError):
        second_adapter.upload_archived_file(
            "message-2",
            _build_transformed_document(),
        )

    assert first_result.success is True
    assert first_adapter.document_storage.list() == [_build_expected_document()]
    assert second_adapter.document_storage.list() == []


def test_mock_storionx_target_adapter_simulates_temporary_service_unavailability() -> None:
    """The adapter should surface temporary 503-style failures structurally."""

    transformed_document = _build_transformed_document()
    adapter = MockStorionXTargetAdapter(
        workspace_id="workspace-1",
        session_id="session-1",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        failure_injector=lambda _document: ServiceUnavailableError(
            retry_after_seconds=2.5,
        ),
    )

    with pytest.raises(ServiceUnavailableError) as exc_info:
        adapter.upload_archived_file(
            transformed_document.source_identifier,
            transformed_document,
        )

    assert exc_info.value.retry_after_seconds == pytest.approx(2.5)
    assert adapter.document_storage.list() == []
