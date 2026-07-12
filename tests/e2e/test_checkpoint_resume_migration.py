"""End-to-end regression tests for checkpoint resume migration execution."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from itertools import count

from adapters.database import InMemoryCheckpointRepository
from adapters.target import MockStorionXTargetAdapter
from application.commands import ResumeMigrationCommand
from application.services import CheckpointService
from application.use_cases.resume_migration import ResumeMigrationUseCase
from migration_engine.orchestrator import MigrationOrchestrator
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
from mock_ev.entities import Archive, Mailbox, MailItem, RetentionPolicy, VaultStore
from mock_storionx.entities import Document
from mock_storionx.services import UploadService
from mock_storionx.storage import DocumentStorage
from ports.identifier_generator_port import IdentifierGeneratorPort


class _DeterministicIdentifierGenerator(IdentifierGeneratorPort):
    """Return predictable identifiers for end-to-end resume tests."""

    def next_archive_id(self) -> str:
        """Return a deterministic archive identifier."""

        return "archive-1"

    def next_mail_item_id(self) -> str:
        """Return a deterministic mail item identifier."""

        return "mail-item-1"

    def next_attachment_id(self) -> str:
        """Return a deterministic attachment identifier."""

        return "attachment-1"

    def next_archived_file_id(self) -> str:
        """Return a deterministic archived file identifier."""

        return "archived-file-1"

    def next_job_id(self) -> str:
        """Return a deterministic migration job identifier."""

        return "migration-1"

    def next_migration_item_id(self) -> str:
        """Return a deterministic migration item identifier."""

        return "migration-item-1"


class _DeterministicPipelineRunner(PipelineRunner):
    """Provide deterministic timestamps for the resume flow."""

    def __init__(
        self,
        *,
        pipeline: MigrationPipeline,
        timestamps: Iterator[datetime],
        checkpoint_service: CheckpointService | None = None,
        identifier_generator: IdentifierGeneratorPort | None = None,
    ) -> None:
        """Create a pipeline runner with a deterministic timestamp source."""

        super().__init__(
            pipeline=pipeline,
            checkpoint_service=checkpoint_service,
            identifier_generator=identifier_generator,
        )
        self._timestamps = timestamps

    def _current_timestamp(self) -> datetime:
        """Return the next deterministic orchestration timestamp."""

        return next(self._timestamps)


class _CountingTargetAdapter(MockStorionXTargetAdapter):
    """Count uploads while using the concrete mock storionX adapter."""

    def __init__(self, *, started_at: datetime) -> None:
        """Create a counting adapter backed by in-memory storionX services."""

        super().__init__(
            started_at=started_at,
            session_id="session-1",
            upload_service=UploadService(),
            document_storage=DocumentStorage(),
        )
        self.upload_calls = 0

    def upload_archived_file(self, archived_file_id: str, payload: object) -> Document:
        """Count upload attempts before delegating to the concrete adapter."""

        self.upload_calls += 1
        return super().upload_archived_file(archived_file_id, payload)


def _build_retention_policy() -> RetentionPolicy:
    """Create a deterministic retention policy for end-to-end resume tests."""

    return RetentionPolicy(
        name="Standard",
        retention_days=30,
        classification="general",
    )


def _build_mail_item() -> MailItem:
    """Create a deterministic Enterprise Vault mail item for end-to-end tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MailItem(
        subject="Quarterly Report",
        sender="sender@example.com",
        body="Body",
        received_at=timestamp,
        sent_at=timestamp,
        modified_at=timestamp,
        internet_message_id="message-1",
        conversation_id="conversation-1",
        message_size=2048,
        retention_policy=_build_retention_policy(),
        recipients=["recipient@example.com"],
        cc_recipients=[],
        bcc_recipients=[],
        attachments=[],
    )


def _build_vault_stores() -> tuple[VaultStore, ...]:
    """Create a tiny deterministic Enterprise Vault dataset."""

    mailbox = Mailbox(address="alice@example.com", mail_items=[_build_mail_item()])
    archive = Archive(name="Archive One", mailboxes=[mailbox])
    vault_store = VaultStore(name="Vault Store One", archives=[archive])
    return (vault_store,)


def _timestamp_sequence() -> Iterator[datetime]:
    """Yield deterministic timestamps for the pipeline runner."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for offset in count():
        yield started_at + timedelta(seconds=offset)


def _build_pipeline(
    *,
    vault_stores: tuple[VaultStore, ...],
    target_port: MockStorionXTargetAdapter,
) -> MigrationPipeline:
    """Create a canonical pipeline for end-to-end resume tests."""

    return MigrationPipeline(
        steps=(
            DiscoverArchivesStep(vault_stores=vault_stores),
            ExtractItemsStep(vault_stores=vault_stores),
            TransformItemsStep(vault_stores=vault_stores),
            UploadItemsStep(target_port=target_port),
            VerifyItemsStep(target_port=target_port),
            FinalizeMigrationStep(),
        ),
    )


def test_checkpoint_resume_migration_completes_without_duplication() -> None:
    """The application use case should resume and finish a checkpointed migration."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    checkpoint_repository = InMemoryCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=checkpoint_repository)
    target_port = _CountingTargetAdapter(started_at=started_at)
    vault_stores = _build_vault_stores()
    identifier_generator = _DeterministicIdentifierGenerator()

    partial_pipeline = MigrationPipeline(
        steps=(
            DiscoverArchivesStep(vault_stores=vault_stores),
            ExtractItemsStep(vault_stores=vault_stores),
            TransformItemsStep(vault_stores=vault_stores),
            UploadItemsStep(target_port=target_port),
        ),
    )
    partial_runner = _DeterministicPipelineRunner(
        pipeline=partial_pipeline,
        timestamps=_timestamp_sequence(),
        checkpoint_service=checkpoint_service,
        identifier_generator=identifier_generator,
    )
    partial_runner.run()

    checkpoint = checkpoint_repository.load_checkpoint("migration-1")
    assert checkpoint is not None
    assert checkpoint.last_completed_step == "UploadItemsStep"
    assert target_port.upload_calls == 1
    assert len(target_port.document_storage.list()) == 1

    resumed_runner = _DeterministicPipelineRunner(
        pipeline=_build_pipeline(vault_stores=vault_stores, target_port=target_port),
        timestamps=_timestamp_sequence(),
        checkpoint_service=checkpoint_service,
        identifier_generator=identifier_generator,
    )
    use_case = ResumeMigrationUseCase(
        checkpoint_service=checkpoint_service,
        migration_orchestrator=MigrationOrchestrator(runner=resumed_runner),
    )

    result = use_case.execute(ResumeMigrationCommand(job_id="migration-1"))

    final_checkpoint = checkpoint_repository.load_checkpoint("migration-1")
    assert result.success is True
    assert final_checkpoint is not None
    assert final_checkpoint.last_completed_step == "FinalizeMigrationStep"
    assert final_checkpoint.current_state == MigrationState.COMPLETED.value
    assert target_port.upload_calls == 1
    assert len(target_port.document_storage.list()) == 1
    assert resumed_runner.current_step_context is not None
    assert resumed_runner.current_step_context.checkpoint == final_checkpoint
    assert resumed_runner.current_step_context.execution_context.state == MigrationState.COMPLETED
    assert resumed_runner.execution_result == result
