"""End-to-end acceptance tests for the migration workflow.

This module exercises the full migration pipeline against deterministic mock
Enterprise Vault source data and the concrete mock storionX target adapter.
The tests verify the orchestration flow, adapter boundaries, deterministic
dataset behavior, and structural preservation of uploaded documents.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import count
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from adapters.source import MockEnterpriseVaultSourceAdapter
from adapters.target import MockStorionXTargetAdapter
from application.dto import UploadResult
from domain.value_objects.identifiers import MigrationItemId
from migration_engine.execution_result import ExecutionResult
from migration_engine.pipeline import MigrationPipeline
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState
from migration_engine.steps import (
    DiscoverArchivesStep,
    ExtractItemsStep,
    FinalizeMigrationStep,
    TransformItemsStep,
    UploadItemsStep,
    VerifyItemsStep,
)
from migration_engine.transformation import TransformedDocument
from mock_ev.builders import EnterpriseVaultBuilder
from mock_ev.entities import VaultStore
from mock_ev.generators import ArchiveGenerator
from mock_storionx.services import UploadService
from mock_storionx.storage import DocumentStorage
from ports import StorionXTargetPort


class _DeterministicPipelineRunner(PipelineRunner):
    """Provide deterministic orchestration timestamps for acceptance tests."""

    def __init__(
        self,
        *,
        pipeline: MigrationPipeline,
        timestamps: Iterator[datetime],
    ) -> None:
        """Create a pipeline runner with a deterministic timestamp source."""

        super().__init__(pipeline=pipeline)
        self._timestamps = timestamps

    def _current_timestamp(self) -> datetime:
        """Return the next deterministic orchestration timestamp."""

        return next(self._timestamps)


class _FailingMockStorionXTargetAdapter(MockStorionXTargetAdapter):
    """Simulate a deterministic upload failure for one document identifier."""

    def __init__(
        self,
        *,
        fail_on_identifier: str,
        workspace_id: str,
        session_id: str,
        started_at: datetime,
        upload_service: UploadService,
        document_storage: DocumentStorage,
    ) -> None:
        """Create a target adapter that fails on the configured identifier."""

        super().__init__(
            workspace_id=workspace_id,
            session_id=session_id,
            started_at=started_at,
            upload_service=upload_service,
            document_storage=document_storage,
        )
        self._fail_on_identifier = fail_on_identifier

    def upload_archived_file(
        self,
        archived_file_id: str,
        payload: object,
    ) -> UploadResult:
        """Upload documents while failing on the configured identifier."""

        if archived_file_id == self._fail_on_identifier:
            if not isinstance(payload, TransformedDocument):
                message = "Unexpected payload"
                raise TypeError(message)

            return UploadResult(
                item_id=MigrationItemId(value=uuid5(NAMESPACE_URL, payload.source_identifier)),
                success=False,
                target_identifier=None,
                error_message=f"upload failed for {archived_file_id}",
                idempotent_replay=False,
            )

        return super().upload_archived_file(archived_file_id, payload)


class _CorruptingMockStorionXTargetAdapter(MockStorionXTargetAdapter):
    """Simulate a deterministic checksum mismatch during verification."""

    def __init__(
        self,
        *,
        corrupt_on_identifier: str,
        workspace_id: str,
        session_id: str,
        started_at: datetime,
        upload_service: UploadService,
        document_storage: DocumentStorage,
    ) -> None:
        """Create a target adapter that corrupts one verification lookup."""

        super().__init__(
            workspace_id=workspace_id,
            session_id=session_id,
            started_at=started_at,
            upload_service=upload_service,
            document_storage=document_storage,
        )
        self._corrupt_on_identifier = corrupt_on_identifier

    def get_uploaded_document(self, document_id: str) -> TransformedDocument | None:
        """Return a mutated uploaded document for the configured identifier."""

        uploaded_document = super().get_uploaded_document(document_id)
        if uploaded_document is None or document_id != self._corrupt_on_identifier:
            return uploaded_document

        return replace(
            uploaded_document,
            checksum=f"{uploaded_document.checksum}-mismatch",
        )


def _build_source_vault_stores(seed: int) -> tuple[VaultStore, ...]:
    """Build a tiny deterministic source dataset for end-to-end tests."""

    archive = ArchiveGenerator(seed=seed).generate_one(
        mailbox_attachment_counts=((1, 0),),
        name="Archive One",
    )
    return (
        EnterpriseVaultBuilder().build_vault_store(
            name="Vault Store One",
            archives=(archive,),
        ),
    )


def _build_source_adapter(seed: int) -> MockEnterpriseVaultSourceAdapter:
    """Build the source adapter for a deterministic test dataset."""

    return MockEnterpriseVaultSourceAdapter(vault_stores=_build_source_vault_stores(seed))


def _build_target_adapter(
    *,
    workspace_id: str = "workspace-1",
    session_id: str = "session-1",
    started_at: datetime | None = None,
) -> MockStorionXTargetAdapter:
    """Build the concrete target adapter with explicit in-memory services."""

    resolved_started_at = started_at or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MockStorionXTargetAdapter(
        workspace_id=workspace_id,
        session_id=session_id,
        started_at=resolved_started_at,
        upload_service=UploadService(),
        document_storage=DocumentStorage(),
    )


def _build_pipeline(
    *,
    vault_stores: tuple[VaultStore, ...],
    target_port: StorionXTargetPort,
) -> MigrationPipeline:
    """Build a concrete pipeline in reverse order to exercise step resolution."""

    steps = (
        FinalizeMigrationStep(),
        VerifyItemsStep(target_port=target_port),
        UploadItemsStep(target_port=target_port),
        TransformItemsStep(vault_stores=vault_stores),
        ExtractItemsStep(vault_stores=vault_stores),
        DiscoverArchivesStep(vault_stores=vault_stores),
    )
    return MigrationPipeline(steps=steps)


def _build_runner(
    *,
    seed: int,
    target_port: StorionXTargetPort | None = None,
    vault_stores: tuple[VaultStore, ...] | None = None,
) -> tuple[_DeterministicPipelineRunner, MockEnterpriseVaultSourceAdapter, StorionXTargetPort]:
    """Build a deterministic runner together with its source and target adapters."""

    source_adapter = (
        _build_source_adapter(seed)
        if vault_stores is None
        else MockEnterpriseVaultSourceAdapter(vault_stores=vault_stores)
    )
    resolved_vault_stores = source_adapter.discover_archives()
    resolved_target_port = target_port or _build_target_adapter()
    pipeline = _build_pipeline(
        vault_stores=resolved_vault_stores,
        target_port=resolved_target_port,
    )
    timestamps = _timestamp_sequence()
    runner = _DeterministicPipelineRunner(
        pipeline=pipeline,
        timestamps=timestamps,
    )
    return runner, source_adapter, resolved_target_port


def _timestamp_sequence() -> Iterator[datetime]:
    """Yield a deterministic timestamp stream for the pipeline runner."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for offset in count():
        yield started_at + timedelta(seconds=offset)


def _source_import_violates_boundary(path: Path) -> bool:
    """Detect direct mock source or target imports in a migration engine module."""

    pattern = re.compile(r"^\s*(from|import)\s+mock_(ev|storionx)\b")
    return any(pattern.search(line) is not None for line in path.read_text().splitlines())


def _run_workflow(
    *,
    seed: int,
    target_port: StorionXTargetPort | None = None,
    vault_stores: tuple[VaultStore, ...] | None = None,
) -> tuple[
    _DeterministicPipelineRunner,
    MockEnterpriseVaultSourceAdapter,
    StorionXTargetPort,
    ExecutionResult,
]:
    """Execute the workflow and return the runner together with its result."""

    runner, source_adapter, resolved_target_port = _build_runner(
        seed=seed,
        target_port=target_port,
        vault_stores=vault_stores,
    )
    result = runner.run()
    return runner, source_adapter, resolved_target_port, result


def test_end_to_end_migration_workflow_completes_successfully() -> None:
    """The full migration workflow should complete successfully end to end."""

    runner, source_adapter, target_port, result = _run_workflow(seed=7)
    assert isinstance(target_port, MockStorionXTargetAdapter)

    source_vault_stores = source_adapter.discover_archives()
    first_archive = source_vault_stores[0].archives[0]
    first_mailbox = first_archive.mailboxes[0]
    expected_document_ids = tuple(
        mail_item.internet_message_id for mail_item in first_mailbox.mail_items
    )

    assert result.success is True
    assert result.execution_report is not None
    assert result.execution_report.completed is True
    assert result.execution_report.failed_steps == 0
    assert result.execution_report.metrics is not None
    assert result.execution_report.metrics.successful_items == 2
    assert result.execution_report.metrics.failed_items == 0
    assert result.execution_report.metrics.verification_failures == 0
    assert result.warnings == ()
    assert runner.state_machine.current_state == MigrationState.COMPLETED
    assert runner.progress_tracker is not None
    assert runner.progress_tracker.current_migration_state == MigrationState.COMPLETED
    assert runner.current_step_context is not None
    assert runner.current_step_context.execution_result == result
    assert runner.current_step_context.discovery_result is not None
    assert runner.current_step_context.extraction_result is not None
    assert runner.current_step_context.transformation_result is not None
    assert runner.current_step_context.upload_result is not None
    assert runner.current_step_context.verification_result is not None
    assert runner.current_step_context.execution_context.state == MigrationState.COMPLETED
    assert runner.current_step_context.upload_result.uploaded_document_ids == expected_document_ids
    assert runner.current_step_context.verification_result.verified_count == 2
    assert isinstance(target_port, MockStorionXTargetAdapter)
    assert target_port.document_storage.list() == [
        target_port.document_storage.get(document_id) for document_id in expected_document_ids
    ]
    assert target_port.upload_service.active_session is not None
    assert target_port.upload_service.active_session.completed_at is not None
    assert source_vault_stores == source_adapter.discover_archives()


def test_end_to_end_migration_workflow_handles_empty_source() -> None:
    """The workflow should complete cleanly when the source is empty."""

    runner, _, target_port, result = _run_workflow(seed=7, vault_stores=())
    assert isinstance(target_port, MockStorionXTargetAdapter)

    assert result.success is True
    assert result.execution_report is not None
    assert result.execution_report.completed is True
    assert runner.current_step_context is not None
    assert runner.current_step_context.discovery_result is not None
    assert runner.current_step_context.discovery_result.archive_count == 0
    assert runner.current_step_context.extraction_result is not None
    assert runner.current_step_context.extraction_result.total_items == 0
    assert runner.current_step_context.transformation_result is not None
    assert runner.current_step_context.transformation_result.transformed_documents == ()
    assert runner.current_step_context.upload_result is not None
    assert runner.current_step_context.upload_result.uploaded_documents == ()
    assert runner.current_step_context.verification_result is not None
    assert runner.current_step_context.verification_result.verified_count == 0
    assert runner.current_step_context.verification_result.failed_count == 0
    assert target_port.document_storage.list() == []
    assert target_port.upload_service.active_session is None


def test_end_to_end_migration_workflow_is_deterministic_for_same_seed() -> None:
    """The same seed should produce the same workflow outcome."""

    first_runner, first_source_adapter, _, first_result = _run_workflow(seed=13)
    second_runner, second_source_adapter, _, second_result = _run_workflow(seed=13)

    assert first_runner.current_step_context is not None
    assert second_runner.current_step_context is not None
    assert first_runner.current_step_context.transformation_result is not None
    assert second_runner.current_step_context.transformation_result is not None
    assert first_runner.current_step_context.upload_result is not None
    assert second_runner.current_step_context.upload_result is not None
    assert first_runner.current_step_context.verification_result is not None
    assert second_runner.current_step_context.verification_result is not None
    assert first_source_adapter.discover_archives() == second_source_adapter.discover_archives()
    assert first_result == second_result
    assert (
        first_runner.current_step_context.transformation_result
        == second_runner.current_step_context.transformation_result
    )
    assert (
        first_runner.current_step_context.upload_result
        == second_runner.current_step_context.upload_result
    )
    assert (
        first_runner.current_step_context.verification_result
        == second_runner.current_step_context.verification_result
    )


def test_end_to_end_migration_workflow_differs_for_different_seed() -> None:
    """Different seeds should produce different source and transformation data."""

    first_runner, first_source_adapter, _, _ = _run_workflow(seed=21)
    second_runner, second_source_adapter, _, _ = _run_workflow(seed=22)

    assert first_runner.current_step_context is not None
    assert second_runner.current_step_context is not None
    assert first_runner.current_step_context.transformation_result is not None
    assert second_runner.current_step_context.transformation_result is not None
    assert first_source_adapter.discover_archives() != second_source_adapter.discover_archives()
    assert (
        first_runner.current_step_context.transformation_result
        != second_runner.current_step_context.transformation_result
    )


def test_end_to_end_migration_workflow_records_partial_upload_failure() -> None:
    """Successful uploads should survive when one document upload fails."""

    source_adapter = _build_source_adapter(seed=31)
    first_archive = source_adapter.load_archive("Archive One")
    assert first_archive is not None
    first_mailbox = first_archive.mailboxes[0]
    failing_identifier = first_mailbox.mail_items[1].internet_message_id
    target_port = _FailingMockStorionXTargetAdapter(
        fail_on_identifier=failing_identifier,
        workspace_id="workspace-1",
        session_id="session-1",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        upload_service=UploadService(),
        document_storage=DocumentStorage(),
    )

    runner, _, resolved_target_port, result = _run_workflow(
        seed=31,
        target_port=target_port,
        vault_stores=source_adapter.discover_archives(),
    )
    assert isinstance(resolved_target_port, _FailingMockStorionXTargetAdapter)

    assert result.success is True
    assert runner.current_step_context is not None
    assert runner.current_step_context.transformation_result is not None
    assert runner.current_step_context.upload_result is not None
    assert runner.current_step_context.upload_result.failed_documents == (
        runner.current_step_context.transformation_result.transformed_documents[1],
    )
    assert runner.current_step_context.upload_result.uploaded_documents == (
        runner.current_step_context.transformation_result.transformed_documents[0],
    )
    assert runner.current_step_context.execution_result is not None
    assert "failed upload" in runner.current_step_context.execution_result.warnings[0]
    assert resolved_target_port.document_storage.list() == [
        resolved_target_port.document_storage.get(
            runner.current_step_context.transformation_result.transformed_documents[
                0
            ].source_identifier,
        )
    ]
    assert resolved_target_port.upload_service.active_session is not None
    assert resolved_target_port.upload_service.active_session.completed_at is not None


def test_end_to_end_migration_workflow_records_verification_mismatch() -> None:
    """A checksum mismatch should be represented structurally in verification."""

    source_adapter = _build_source_adapter(seed=41)
    first_archive = source_adapter.load_archive("Archive One")
    assert first_archive is not None
    first_identifier = first_archive.mailboxes[0].mail_items[0].internet_message_id
    target_port = _CorruptingMockStorionXTargetAdapter(
        corrupt_on_identifier=first_identifier,
        workspace_id="workspace-1",
        session_id="session-1",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        upload_service=UploadService(),
        document_storage=DocumentStorage(),
    )

    runner, _, resolved_target_port, result = _run_workflow(
        seed=41,
        target_port=target_port,
        vault_stores=source_adapter.discover_archives(),
    )
    assert isinstance(resolved_target_port, _CorruptingMockStorionXTargetAdapter)

    assert result.success is True
    assert runner.current_step_context is not None
    assert runner.current_step_context.verification_result is not None
    assert runner.current_step_context.verification_result.failed_count == 1
    assert runner.current_step_context.verification_result.checksum_mismatches == (
        first_identifier,
    )
    assert runner.current_step_context.execution_result is not None
    assert "failed verification" in runner.current_step_context.execution_result.warnings[0]
    assert resolved_target_port.document_storage.list()


def test_source_and_target_adapter_contracts_remain_target_neutral() -> None:
    """The source and target adapters should expose the expected boundaries."""

    source_adapter = _build_source_adapter(seed=55)
    vault_stores = source_adapter.discover_archives()
    archive = source_adapter.load_archive("Archive One")
    assert archive is not None
    assert len(source_adapter.stream_mail_items("Archive One")) == 2
    assert len(source_adapter.stream_attachments("Archive One")) == 1

    target_adapter = _build_target_adapter()
    archive_document = TransformedDocument(
        source_identifier=archive.mailboxes[0].mail_items[0].internet_message_id,
        archive_name=archive.name,
        mailbox_address=archive.mailboxes[0].address,
        subject=archive.mailboxes[0].mail_items[0].subject,
        filename=f"{archive.mailboxes[0].mail_items[0].subject}.eml",
        content_type="message/rfc822",
        size_bytes=archive.mailboxes[0].mail_items[0].message_size
        + archive.mailboxes[0].mail_items[0].attachments[0].size_bytes,
        checksum=archive.mailboxes[0].mail_items[0].internet_message_id,
        sender=archive.mailboxes[0].mail_items[0].sender,
        recipients=tuple(archive.mailboxes[0].mail_items[0].recipients),
        cc_recipients=tuple(archive.mailboxes[0].mail_items[0].cc_recipients),
        bcc_recipients=tuple(archive.mailboxes[0].mail_items[0].bcc_recipients),
        retention_policy=archive.mailboxes[0].mail_items[0].retention_policy.name,
        department="Example",
        tags=(archive.name, archive.mailboxes[0].address),
        custom_properties=(
            (
                "internet_message_id",
                archive.mailboxes[0].mail_items[0].internet_message_id,
            ),
        ),
        attachment_filenames=(archive.mailboxes[0].mail_items[0].attachments[0].filename,),
        attachment_checksums=(archive.mailboxes[0].mail_items[0].attachments[0].checksum,),
        attachment_sizes=(archive.mailboxes[0].mail_items[0].attachments[0].size_bytes,),
        created_at=archive.mailboxes[0].mail_items[0].sent_at,
        modified_at=archive.mailboxes[0].mail_items[0].modified_at,
    )

    upload_result = target_adapter.upload_archived_file(
        archive_document.source_identifier,
        archive_document,
    )

    stored_document = target_adapter.document_storage.get(archive_document.source_identifier)
    assert stored_document is not None
    assert upload_result.success is True
    assert upload_result.idempotent_replay is False
    assert (
        target_adapter.get_uploaded_document(
            archive_document.source_identifier,
        )
        == archive_document
    )
    assert (
        target_adapter.document_storage.get(
            archive_document.source_identifier,
        )
        == stored_document
    )
    assert target_adapter.document_storage.list() == [stored_document]
    assert vault_stores == source_adapter.discover_archives()


def test_migration_engine_has_no_direct_mock_imports() -> None:
    """The migration engine must not import mock source or target modules directly."""

    migration_engine_dir = Path(__file__).resolve().parents[2] / "src" / "migration_engine"
    assert all(
        not _source_import_violates_boundary(path) for path in migration_engine_dir.rglob("*.py")
    )
