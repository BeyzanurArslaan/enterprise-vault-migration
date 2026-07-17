"""End-to-end regression tests for idempotent retry and resume execution.

This module verifies that a lost upload response can be retried safely without
creating duplicate target documents and that a later checkpoint resume
continues from the uploaded state without re-uploading the same document.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from itertools import count

from adapters.database import InMemoryCheckpointRepository, InMemoryRetryRepository
from adapters.target import MockStorionXTargetAdapter
from application.commands import ResumeMigrationCommand
from application.dto import UploadResult
from application.services import CheckpointService
from application.use_cases.resume_migration import ResumeMigrationUseCase
from domain.enums.retry_strategy import RetryStrategy
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ProgressSnapshot
from migration_engine.orchestrator import MigrationOrchestrator
from migration_engine.pipeline import MigrationPipeline
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.retry import RetryPolicy
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import (
    DiscoverArchivesStep,
    ExtractItemsStep,
    FinalizeMigrationStep,
    TransformItemsStep,
    UploadItemsStep,
    VerifyItemsStep,
)
from mock_ev.entities import Archive, Mailbox, MailItem, RetentionPolicy, VaultStore
from mock_storionx.storage import DocumentStorage
from ports.identifier_generator_port import IdentifierGeneratorPort


class _DeterministicIdentifierGenerator(IdentifierGeneratorPort):
    """Return predictable identifiers for the end-to-end idempotency test."""

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
    """Provide deterministic timestamps for the end-to-end idempotency test."""

    def __init__(
        self,
        *,
        pipeline: MigrationPipeline,
        timestamps: Iterator[datetime],
        checkpoint_service: CheckpointService | None = None,
        retry_policy: RetryPolicy | None = None,
        retry_repository: InMemoryRetryRepository | None = None,
        retry_classifier: Callable[[Exception], bool] | None = None,
        sleeper: Callable[[float], None] | None = None,
        identifier_generator: IdentifierGeneratorPort | None = None,
        initial_context: MigrationStepContext | None = None,
    ) -> None:
        """Create a runner with a deterministic timestamp source."""

        super().__init__(
            pipeline=pipeline,
            initial_context=initial_context,
            checkpoint_service=checkpoint_service,
            retry_policy=retry_policy,
            retry_repository=retry_repository,
            retry_classifier=retry_classifier,
            sleeper=sleeper,
            identifier_generator=identifier_generator,
        )
        self._timestamps = timestamps

    def _current_timestamp(self) -> datetime:
        """Return the next deterministic orchestration timestamp."""

        return next(self._timestamps)


class _FlakyIdempotentTargetAdapter(MockStorionXTargetAdapter):
    """Simulate a response loss after a successful upload stores the document."""

    def __init__(self, *, started_at: datetime) -> None:
        """Create an adapter that fails once after storing the first document."""

        super().__init__(
            started_at=started_at,
            session_id="session-1",
            document_storage=DocumentStorage(),
        )
        self._response_loss_triggered = False

    def upload_archived_file(
        self,
        archived_file_id: str,
        payload: object,
    ) -> UploadResult:
        """Lose the first successful response after the document is stored."""

        upload_result = super().upload_archived_file(archived_file_id, payload)
        if not self._response_loss_triggered:
            self._response_loss_triggered = True
            message = "transient upload response loss"
            raise RuntimeError(message)

        return upload_result


def _build_retention_policy() -> RetentionPolicy:
    """Create a deterministic retention policy for the end-to-end test."""

    return RetentionPolicy(
        name="Standard",
        retention_days=30,
        classification="general",
    )


def _build_mail_item() -> MailItem:
    """Create a deterministic Enterprise Vault mail item for the test."""

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


def _build_initial_context() -> MigrationStepContext:
    """Build a deterministic initial context with an active archive filter."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    progress_tracker = ProgressTracker(
        snapshot=ProgressSnapshot(
            total_items=0,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            current_archive=None,
            current_mailbox=None,
            current_item=None,
            started_at=started_at,
            last_updated=started_at,
        ),
        migration_state=MigrationState.CREATED,
    )
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(archive_names=("Archive One",)),
        started_at=started_at,
        current_step=None,
        progress_tracker=progress_tracker,
        state=MigrationState.CREATED,
        current_timestamp=started_at,
    )
    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=progress_tracker,
        state_machine=None,
    )


def _build_partial_pipeline(
    *,
    vault_stores: tuple[VaultStore, ...],
    target_port: MockStorionXTargetAdapter,
) -> MigrationPipeline:
    """Create the partial pipeline used before the checkpoint resume."""

    return MigrationPipeline(
        steps=(
            DiscoverArchivesStep(vault_stores=vault_stores),
            ExtractItemsStep(vault_stores=vault_stores),
            TransformItemsStep(vault_stores=vault_stores),
            UploadItemsStep(target_port=target_port),
        ),
    )


def _build_full_pipeline(
    *,
    vault_stores: tuple[VaultStore, ...],
    target_port: MockStorionXTargetAdapter,
) -> MigrationPipeline:
    """Create the full pipeline used after checkpoint resume."""

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


def test_idempotent_retry_and_resume_do_not_duplicate_target_documents() -> None:
    """Retrying a lost response and resuming from the checkpoint should stay idempotent."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    retry_repository = InMemoryRetryRepository()
    checkpoint_repository = InMemoryCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=checkpoint_repository)
    target_port = _FlakyIdempotentTargetAdapter(started_at=started_at)
    vault_stores = _build_vault_stores()
    identifier_generator = _DeterministicIdentifierGenerator()

    partial_runner = _DeterministicPipelineRunner(
        pipeline=_build_partial_pipeline(
            vault_stores=vault_stores,
            target_port=target_port,
        ),
        timestamps=_timestamp_sequence(),
        checkpoint_service=checkpoint_service,
        initial_context=_build_initial_context(),
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=3,
            fixed_delay_seconds=1.0,
        ),
        retry_repository=retry_repository,
        retry_classifier=lambda exception: isinstance(exception, RuntimeError),
        sleeper=lambda _delay: None,
        identifier_generator=identifier_generator,
    )

    partial_result = partial_runner.run()

    assert partial_result.success is True
    assert len(target_port.document_storage.list()) == 1
    checkpoint = checkpoint_repository.load_checkpoint("migration-1")
    assert checkpoint is not None
    assert checkpoint.last_completed_step == "UploadItemsStep"
    assert len(retry_repository.list_for_job("migration-1")) == 1

    resumed_runner = _DeterministicPipelineRunner(
        pipeline=_build_full_pipeline(
            vault_stores=vault_stores,
            target_port=target_port,
        ),
        timestamps=_timestamp_sequence(),
        checkpoint_service=checkpoint_service,
        identifier_generator=identifier_generator,
    )
    use_case = ResumeMigrationUseCase(
        checkpoint_service=checkpoint_service,
        migration_orchestrator=MigrationOrchestrator(runner=resumed_runner),
    )

    resumed_result = use_case.execute(ResumeMigrationCommand(job_id="migration-1"))

    assert resumed_result.success is True
    assert resumed_runner.state_machine.current_state == MigrationState.COMPLETED
    assert len(target_port.document_storage.list()) == 1
    assert resumed_runner.current_step_context is not None
    assert resumed_runner.current_step_context.verification_result is not None
    assert resumed_runner.current_step_context.verification_result.verified_count == 1
    assert resumed_result.execution_report is not None
    assert resumed_result.execution_report.final_status == "completed"
    assert resumed_result.execution_report.resumed is True
    assert resumed_result.execution_report.summary is not None
    assert "Archive filters: Archive One" in resumed_result.execution_report.summary
