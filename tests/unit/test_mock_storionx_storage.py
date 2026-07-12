"""Unit tests for the mock storionX in-memory storage layer."""

from __future__ import annotations

from datetime import UTC, datetime

from mock_storionx.entities import Document, Folder, Metadata, UploadSession, Workspace
from mock_storionx.storage import (
    DocumentStorage,
    FolderStorage,
    MetadataStorage,
    UploadSessionStorage,
    WorkspaceStorage,
)


def _build_workspace() -> Workspace:
    """Create a sample workspace entity for storage tests."""

    return Workspace(id="ws-1", name="Workspace One", description="Primary workspace")


def _build_folder() -> Folder:
    """Create a sample folder entity for storage tests."""

    return Folder(id="folder-1", name="Inbox", path="/Inbox")


def _build_metadata() -> Metadata:
    """Create a sample metadata entity for storage tests."""

    return Metadata(
        author="Alicia Patel",
        department="Finance",
        retention_policy="Standard",
        tags=["finance", "mail"],
        custom_properties={"region": "emea"},
    )


def _build_document() -> Document:
    """Create a sample document entity for storage tests."""

    return Document(
        id="doc-1",
        filename="report.pdf",
        content_type="application/pdf",
        size=1024,
        checksum="checksum-1",
        metadata=_build_metadata(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        modified_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


def _build_upload_session() -> UploadSession:
    """Create a sample upload session entity for storage tests."""

    return UploadSession(
        id="session-1",
        workspace_id="ws-1",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=None,
        uploaded_documents=[_build_document()],
    )


def test_workspace_storage_supports_crud_operations() -> None:
    """Workspace storage should add, get, list, and remove workspaces."""

    storage = WorkspaceStorage()
    workspace = _build_workspace()

    storage.add(workspace)

    assert storage.get("ws-1") == workspace
    assert storage.list() == [workspace]

    storage.remove("ws-1")

    assert storage.get("ws-1") is None
    assert storage.list() == []


def test_folder_storage_supports_crud_operations() -> None:
    """Folder storage should add, get, list, and remove folders."""

    storage = FolderStorage()
    folder = _build_folder()

    storage.add(folder)

    assert storage.get("folder-1") == folder
    assert storage.list() == [folder]

    storage.remove("folder-1")

    assert storage.get("folder-1") is None
    assert storage.list() == []


def test_document_storage_supports_crud_operations() -> None:
    """Document storage should add, get, list, and remove documents."""

    storage = DocumentStorage()
    document = _build_document()

    storage.add(document)

    assert storage.get("doc-1") == document
    assert storage.list() == [document]

    storage.remove("doc-1")

    assert storage.get("doc-1") is None
    assert storage.list() == []


def test_upload_session_storage_supports_crud_operations() -> None:
    """Upload session storage should add, get, list, and remove sessions."""

    storage = UploadSessionStorage()
    session = _build_upload_session()

    storage.add(session)

    assert storage.get("session-1") == session
    assert storage.list() == [session]

    storage.remove("session-1")

    assert storage.get("session-1") is None
    assert storage.list() == []


def test_metadata_storage_supports_crud_operations() -> None:
    """Metadata storage should add, get, list, and remove metadata records."""

    storage = MetadataStorage()
    metadata = _build_metadata()
    metadata_key = "Alicia Patel|Finance|Standard"

    storage.add(metadata)

    assert storage.get(metadata_key) == metadata
    assert storage.list() == [metadata]

    storage.remove(metadata_key)

    assert storage.get(metadata_key) is None
    assert storage.list() == []
