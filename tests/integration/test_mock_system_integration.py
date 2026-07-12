"""Integration tests covering the mock source and target subsystems.

These tests validate that the synthetic Enterprise Vault dataset generator and
the mock storionX façade can be instantiated and exercised together without
introducing persistence, networking, or migration-engine dependencies.
"""

from __future__ import annotations

from hashlib import sha256

from mock_ev.entities import VaultStore
from mock_ev.generators import (
    SMALL_PROFILE,
    AttachmentGenerator,
    DatasetGenerator,
    FixtureLoader,
)
from mock_storionx.api import HealthAPI, MetadataAPI, SearchAPI, UploadAPI
from mock_storionx.entities import Document, Folder, Metadata, UploadSession, Workspace
from mock_storionx.services import MetadataService, SearchService, UploadService
from mock_storionx.storage import (
    DocumentStorage,
    FolderStorage,
    MetadataStorage,
    UploadSessionStorage,
    WorkspaceStorage,
)


def _count_archives(dataset: list[VaultStore]) -> int:
    """Count archives across a generated dataset."""

    return sum(len(vault_store.archives) for vault_store in dataset)


def _count_mailboxes(dataset: list[VaultStore]) -> int:
    """Count mailboxes across a generated dataset."""

    return sum(
        len(archive.mailboxes) for vault_store in dataset for archive in vault_store.archives
    )


def _count_mail_items(dataset: list[VaultStore]) -> int:
    """Count mail items across a generated dataset."""

    return sum(
        len(mailbox.mail_items)
        for vault_store in dataset
        for archive in vault_store.archives
        for mailbox in archive.mailboxes
    )


def _count_attachments(dataset: list[VaultStore]) -> int:
    """Count attachments across a generated dataset."""

    return sum(
        len(mail_item.attachments)
        for vault_store in dataset
        for archive in vault_store.archives
        for mailbox in archive.mailboxes
        for mail_item in mailbox.mail_items
    )


def _build_workspace() -> Workspace:
    """Create a sample workspace entity for integration tests."""

    return Workspace(id="ws-1", name="Workspace One", description="Primary workspace")


def _build_folder() -> Folder:
    """Create a sample folder entity for integration tests."""

    return Folder(id="folder-1", name="Inbox", path="/Inbox")


def _build_metadata() -> Metadata:
    """Create a sample metadata entity for integration tests."""

    return Metadata(
        author="Alicia Patel",
        department="Finance",
        retention_policy="Standard",
        tags=["finance", "mail"],
        custom_properties={"region": "emea"},
    )


def _build_document() -> Document:
    """Create a sample document entity for integration tests."""

    from datetime import UTC, datetime

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
    """Create a sample upload session entity for integration tests."""

    from datetime import UTC, datetime

    return UploadSession(
        id="session-1",
        workspace_id="ws-1",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=None,
        uploaded_documents=[_build_document()],
    )


def test_small_dataset_generation_exposes_expected_content() -> None:
    """A SMALL Enterprise Vault dataset should expose the expected counts."""

    dataset = DatasetGenerator(seed=7).generate_small()

    assert len(dataset) == SMALL_PROFILE.vault_stores
    assert _count_archives(dataset) == SMALL_PROFILE.archives
    assert _count_mailboxes(dataset) == SMALL_PROFILE.mailboxes
    assert _count_mail_items(dataset) == SMALL_PROFILE.mail_items
    assert _count_attachments(dataset) == SMALL_PROFILE.attachments


def test_mock_storionx_api_facades_can_be_instantiated() -> None:
    """The mock storionX API façade classes should instantiate cleanly."""

    assert UploadAPI() is not None
    assert SearchAPI() is not None
    assert MetadataAPI() is not None
    assert HealthAPI() is not None


def test_mock_storionx_services_expose_expected_public_interfaces() -> None:
    """The mock storionX services should expose the expected public methods."""

    upload_service = UploadService()
    search_service = SearchService()
    metadata_service = MetadataService()
    workspace = _build_workspace()
    folder = _build_folder()
    metadata = _build_metadata()
    document = _build_document()

    assert callable(upload_service.create_upload_session)
    assert callable(upload_service.upload_document)
    assert callable(upload_service.finalize_upload)
    assert callable(search_service.search_documents)
    assert callable(search_service.search_by_metadata)
    assert callable(search_service.search_by_workspace)
    assert callable(search_service.search_by_folder)
    assert callable(metadata_service.create_metadata)
    assert callable(metadata_service.update_metadata)
    assert callable(metadata_service.get_metadata)
    assert callable(metadata_service.delete_metadata)
    assert callable(metadata_service.list_metadata)

    assert metadata_service.create_metadata(document=document, metadata=metadata) == metadata
    assert metadata_service.update_metadata(document=document, metadata=metadata) == metadata
    assert metadata_service.get_metadata(document=document) == metadata
    assert metadata_service.list_metadata(workspace=workspace) == []
    assert search_service.search_documents(query="report", workspace=workspace, folder=folder) == []
    assert search_service.search_by_metadata(metadata=metadata) == []
    assert search_service.search_by_workspace(workspace=workspace) == []
    assert search_service.search_by_folder(folder=folder) == []

    session = upload_service.create_upload_session(workspace_id=workspace.id)
    assert session.workspace_id == workspace.id
    assert upload_service.upload_document(document=document).uploaded_documents == [document]
    assert upload_service.finalize_upload().completed_at is not None


def test_in_memory_storage_crud_operations_work() -> None:
    """The in-memory storages should support add, get, list, and remove."""

    workspace_storage = WorkspaceStorage()
    folder_storage = FolderStorage()
    document_storage = DocumentStorage()
    upload_session_storage = UploadSessionStorage()
    metadata_storage = MetadataStorage()

    workspace = _build_workspace()
    folder = _build_folder()
    document = _build_document()
    upload_session = _build_upload_session()
    metadata = _build_metadata()
    metadata_key = "|".join((metadata.author, metadata.department, metadata.retention_policy))

    workspace_storage.add(workspace)
    folder_storage.add(folder)
    document_storage.add(document)
    upload_session_storage.add(upload_session)
    metadata_storage.add(metadata)

    assert workspace_storage.get(workspace.id) == workspace
    assert folder_storage.get(folder.id) == folder
    assert document_storage.get(document.id) == document
    assert upload_session_storage.get(upload_session.id) == upload_session
    assert metadata_storage.get(metadata_key) == metadata
    assert workspace_storage.list() == [workspace]
    assert folder_storage.list() == [folder]
    assert document_storage.list() == [document]
    assert upload_session_storage.list() == [upload_session]
    assert metadata_storage.list() == [metadata]

    workspace_storage.remove(workspace.id)
    folder_storage.remove(folder.id)
    document_storage.remove(document.id)
    upload_session_storage.remove(upload_session.id)
    metadata_storage.remove(metadata_key)

    assert workspace_storage.get(workspace.id) is None
    assert folder_storage.get(folder.id) is None
    assert document_storage.get(document.id) is None
    assert upload_session_storage.get(upload_session.id) is None
    assert metadata_storage.get(metadata_key) is None


def test_dataset_generator_is_deterministic() -> None:
    """The dataset generator should be deterministic for a fixed seed."""

    seeded_generator = DatasetGenerator(seed=17)
    matching_generator = DatasetGenerator(seed=17)
    different_generator = DatasetGenerator(seed=18)

    assert seeded_generator.generate_small() == matching_generator.generate_small()
    assert seeded_generator.generate_small() != different_generator.generate_small()


def test_fixture_loader_returns_expected_fixture_records() -> None:
    """The fixture loader should return the expected fixture collections."""

    loader = FixtureLoader()

    users = loader.load_users()
    departments = loader.load_departments()
    mail_subjects = loader.load_mail_subjects()
    attachment_names = loader.load_attachment_names()
    retention_policies = loader.load_retention_policies()

    assert users
    assert departments
    assert mail_subjects
    assert attachment_names
    assert retention_policies
    assert users[0].department in {department.name for department in departments}
    assert isinstance(mail_subjects[0], str)
    assert isinstance(attachment_names[0], str)
    assert isinstance(retention_policies[0].name, str)


def test_attachment_generator_produces_sha256_checksums() -> None:
    """The attachment generator should compute checksums with SHA-256."""

    attachment = AttachmentGenerator(seed=3).generate_one(
        filename="report.pdf",
        mime_type="application/pdf",
        size_bytes=128,
    )

    expected_checksum = sha256(b"report.pdf|pdf|application/pdf|128").hexdigest()

    assert attachment.checksum == expected_checksum
