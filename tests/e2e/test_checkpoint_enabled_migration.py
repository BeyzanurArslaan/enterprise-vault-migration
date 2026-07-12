"""End-to-end regression tests for checkpoint-enabled migration execution."""

from __future__ import annotations

from datetime import UTC, datetime

from adapters.database import InMemoryCheckpointRepository
from adapters.target import MockStorionXTargetAdapter
from application.services import CheckpointService
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ProgressSnapshot
from migration_engine.metrics import MigrationMetrics
from migration_engine.pipeline import MigrationPipeline
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState, MigrationStateMachine
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


def _build_retention_policy() -> RetentionPolicy:
    """Create a deterministic retention policy for the end-to-end test."""

    return RetentionPolicy(
        name="Standard",
        retention_days=30,
        classification="general",
    )


def _build_mail_item() -> MailItem:
    """Create a deterministic Enterprise Vault mail item for the end-to-end test."""

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
    """Create a small deterministic Enterprise Vault dataset."""

    mailbox = Mailbox(
        address="alice@example.com",
        mail_items=[_build_mail_item()],
    )
    archive = Archive(name="Archive One", mailboxes=[mailbox])
    vault_store = VaultStore(name="Vault Store One", archives=[archive])
    return (vault_store,)


def _build_progress_tracker(started_at: datetime) -> ProgressTracker:
    """Create a deterministic progress tracker for the end-to-end workflow."""

    return ProgressTracker(
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


def _build_initial_context(started_at: datetime) -> MigrationStepContext:
    """Create the initial migration step context for the end-to-end workflow."""

    progress_tracker = _build_progress_tracker(started_at)
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step=None,
        metrics=MigrationMetrics(
            duration_seconds=0.0,
            throughput_items_per_second=0.0,
            average_item_size=0,
            processed_bytes=0,
            estimated_remaining_seconds=None,
            peak_memory_usage_mb=None,
            total_items=0,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            retried_items=0,
            uploaded_items=0,
            verification_failures=0,
            total_bytes=0,
            started_at=started_at,
            finished_at=started_at,
        ),
        progress_tracker=progress_tracker,
        state=MigrationState.CREATED,
        current_timestamp=started_at,
    )
    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=progress_tracker,
        state_machine=MigrationStateMachine(current_state=MigrationState.CREATED),
    )


def test_checkpoint_enabled_migration_stores_final_checkpoint() -> None:
    """The full concrete migration workflow should persist its final checkpoint."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    checkpoint_repository = InMemoryCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=checkpoint_repository)
    target_port = MockStorionXTargetAdapter(
        started_at=started_at,
        session_id="session-1",
    )
    vault_stores = _build_vault_stores()
    pipeline = MigrationPipeline(
        steps=(
            FinalizeMigrationStep(),
            VerifyItemsStep(target_port=target_port),
            UploadItemsStep(target_port=target_port),
            TransformItemsStep(vault_stores=vault_stores),
            ExtractItemsStep(),
            DiscoverArchivesStep(vault_stores=vault_stores),
        ),
    )
    runner = PipelineRunner(
        pipeline.steps,
        pipeline=pipeline,
        initial_context=_build_initial_context(started_at),
        checkpoint_service=checkpoint_service,
    )

    result = runner.run()
    final_checkpoint = checkpoint_repository.load_checkpoint("migration-1")

    assert result.success is True
    assert final_checkpoint is not None
    assert final_checkpoint.checkpoint_id == "migration-1:FinalizeMigrationStep"
    assert final_checkpoint.migration_job_id == "migration-1"
    assert final_checkpoint.last_completed_step == "FinalizeMigrationStep"
    assert final_checkpoint.last_processed_item_id == "message-1"
    assert final_checkpoint.current_state == MigrationState.COMPLETED.value
    assert final_checkpoint.processed_items == 1
    assert final_checkpoint.successful_items == 1
    assert final_checkpoint.failed_items == 0
    assert final_checkpoint.uploaded_items == 1
    assert final_checkpoint.verification_failures == 0
    assert final_checkpoint.version == 1
    assert runner.current_step_context is not None
    assert runner.current_step_context.checkpoint == final_checkpoint
    assert runner.current_step_context.execution_result is not None
