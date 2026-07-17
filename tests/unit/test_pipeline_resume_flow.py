"""Regression tests for checkpoint-driven pipeline resume flow."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from itertools import count

from adapters.database import InMemoryCheckpointRepository
from adapters.target import MockStorionXTargetAdapter
from application.dto import UploadResult
from application.services import CheckpointService
from migration_engine.contracts import PipelineStep
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
from mock_storionx.services import UploadService
from mock_storionx.storage import DocumentStorage
from ports.identifier_generator_port import IdentifierGeneratorPort


class _DeterministicIdentifierGenerator(IdentifierGeneratorPort):
    """Return predictable identifiers for resume flow tests."""

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
    """Provide deterministic timestamps for pipeline resume tests."""

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

    def upload_archived_file(
        self,
        archived_file_id: str,
        payload: object,
    ) -> UploadResult:
        """Count upload attempts before delegating to the concrete adapter."""

        self.upload_calls += 1
        return super().upload_archived_file(archived_file_id, payload)


def _build_retention_policy() -> RetentionPolicy:
    """Create a deterministic retention policy for resume tests."""

    return RetentionPolicy(
        name="Standard",
        retention_days=30,
        classification="general",
    )


def _build_mail_item() -> MailItem:
    """Create a deterministic Enterprise Vault mail item for resume tests."""

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


def _build_steps(
    *,
    vault_stores: tuple[VaultStore, ...],
    target_port: MockStorionXTargetAdapter,
) -> tuple[
    DiscoverArchivesStep,
    ExtractItemsStep,
    TransformItemsStep,
    UploadItemsStep,
    VerifyItemsStep,
    FinalizeMigrationStep,
]:
    """Create the canonical migration steps for a deterministic pipeline."""

    return (
        DiscoverArchivesStep(vault_stores=vault_stores),
        ExtractItemsStep(vault_stores=vault_stores),
        TransformItemsStep(vault_stores=vault_stores),
        UploadItemsStep(target_port=target_port),
        VerifyItemsStep(target_port=target_port),
        FinalizeMigrationStep(),
    )


def _timestamp_sequence() -> Iterator[datetime]:
    """Yield deterministic timestamps for the pipeline runner."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for offset in count():
        yield started_at + timedelta(seconds=offset)


def _build_pipeline(steps: tuple[PipelineStep, ...]) -> MigrationPipeline:
    """Create a pipeline from ordered step instances."""

    return MigrationPipeline(steps=steps)


def test_pipeline_runner_resumes_from_each_checkpoint_stage() -> None:
    """The runner should resume from every supported checkpoint stage."""

    for completed_step_count in (1, 2, 3, 4, 5):
        vault_stores = _build_vault_stores()
        checkpoint_repository = InMemoryCheckpointRepository()
        checkpoint_service = CheckpointService(checkpoint_repository=checkpoint_repository)
        started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        target_port = _CountingTargetAdapter(started_at=started_at)
        steps = _build_steps(vault_stores=vault_stores, target_port=target_port)
        identifier_generator = _DeterministicIdentifierGenerator()

        partial_pipeline = _build_pipeline(steps[:completed_step_count])
        partial_runner = _DeterministicPipelineRunner(
            pipeline=partial_pipeline,
            timestamps=_timestamp_sequence(),
            checkpoint_service=checkpoint_service,
            identifier_generator=identifier_generator,
        )
        partial_runner.run()
        checkpoint = checkpoint_repository.load_checkpoint("migration-1")
        assert checkpoint is not None
        assert checkpoint.last_completed_step == steps[completed_step_count - 1].__class__.__name__

        resumed_pipeline = _build_pipeline(steps)
        resumed_runner = _DeterministicPipelineRunner(
            pipeline=resumed_pipeline,
            timestamps=_timestamp_sequence(),
            checkpoint_service=checkpoint_service,
            identifier_generator=identifier_generator,
        )
        result = resumed_runner.run(resume_checkpoint=checkpoint)

        final_checkpoint = checkpoint_repository.load_checkpoint("migration-1")
        assert result.success is True
        assert final_checkpoint is not None
        assert final_checkpoint.last_completed_step == "FinalizeMigrationStep"
        assert final_checkpoint.current_state == MigrationState.COMPLETED.value
        assert resumed_runner.current_step_context is not None
        assert resumed_runner.current_step_context.checkpoint == final_checkpoint
        assert (
            resumed_runner.current_step_context.execution_context.state == MigrationState.COMPLETED
        )
        assert resumed_runner.current_step_context.progress_tracker is not None
        assert (
            resumed_runner.current_step_context.progress_tracker.current_snapshot.processed_items
            == 1
        )
        assert (
            resumed_runner.current_step_context.progress_tracker.current_snapshot.successful_items
            == 1
        )
        assert target_port.upload_calls == 1
        assert len(target_port.document_storage.list()) == 1
        assert resumed_runner.execution_result == result


def test_pipeline_runner_resume_matches_fresh_execution_for_same_source() -> None:
    """The same checkpoint and source should produce the same final outcome."""

    vault_stores = _build_vault_stores()
    target_started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    resumed_target_port = _CountingTargetAdapter(started_at=target_started_at)
    resumed_steps = _build_steps(vault_stores=vault_stores, target_port=resumed_target_port)
    resumed_repository = InMemoryCheckpointRepository()
    resumed_checkpoint_service = CheckpointService(
        checkpoint_repository=resumed_repository,
    )
    identifier_generator = _DeterministicIdentifierGenerator()

    partial_pipeline = _build_pipeline(resumed_steps[:4])
    partial_runner = _DeterministicPipelineRunner(
        pipeline=partial_pipeline,
        timestamps=_timestamp_sequence(),
        checkpoint_service=resumed_checkpoint_service,
        identifier_generator=identifier_generator,
    )
    partial_runner.run()
    checkpoint = resumed_repository.load_checkpoint("migration-1")
    assert checkpoint is not None

    resumed_pipeline = _build_pipeline(resumed_steps)
    resumed_runner = _DeterministicPipelineRunner(
        pipeline=resumed_pipeline,
        timestamps=_timestamp_sequence(),
        checkpoint_service=resumed_checkpoint_service,
        identifier_generator=identifier_generator,
    )
    resumed_result = resumed_runner.run(resume_checkpoint=checkpoint)

    fresh_target_port = _CountingTargetAdapter(started_at=target_started_at)
    fresh_steps = _build_steps(vault_stores=vault_stores, target_port=fresh_target_port)
    fresh_runner = _DeterministicPipelineRunner(
        pipeline=_build_pipeline(fresh_steps),
        timestamps=_timestamp_sequence(),
        checkpoint_service=None,
        identifier_generator=identifier_generator,
    )
    fresh_result = fresh_runner.run()

    assert resumed_result.success is True
    assert fresh_result.success is True
    assert resumed_result.execution_report is not None
    assert fresh_result.execution_report is not None
    assert resumed_result.execution_report.completed == fresh_result.execution_report.completed
    assert (
        resumed_result.execution_report.successful_steps
        == fresh_result.execution_report.successful_steps
    )
    assert (
        resumed_result.execution_report.failed_steps == fresh_result.execution_report.failed_steps
    )
    assert (
        resumed_result.execution_report.skipped_steps == fresh_result.execution_report.skipped_steps
    )
    assert resumed_result.metrics is not None
    assert fresh_result.metrics is not None
    assert resumed_result.metrics.total_items == fresh_result.metrics.total_items == 1
    assert resumed_result.metrics.processed_items == fresh_result.metrics.processed_items == 1
    assert resumed_result.metrics.successful_items == fresh_result.metrics.successful_items == 1
    assert resumed_result.metrics.failed_items == fresh_result.metrics.failed_items == 0
    assert resumed_result.metrics.uploaded_items == fresh_result.metrics.uploaded_items == 1
    assert (
        resumed_result.metrics.verification_failures
        == fresh_result.metrics.verification_failures
        == 0
    )
    assert resumed_target_port.upload_calls == 1
    assert fresh_target_port.upload_calls == 1
    assert len(resumed_target_port.document_storage.list()) == 1
    assert len(fresh_target_port.document_storage.list()) == 1
