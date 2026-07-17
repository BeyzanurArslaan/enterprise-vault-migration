"""Regression tests for automatic checkpoint persistence in the pipeline runner."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path

from application.services import CheckpointService
from migration_engine.checkpoint import CheckpointSnapshot
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import (
    ExecutionContext,
    ExecutionReport,
    PipelineStep,
    ProgressSnapshot,
)
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState
from migration_engine.step_context import MigrationStepContext
from ports import CheckpointRepositoryPort
from ports.identifier_generator_port import IdentifierGeneratorPort


def _build_metrics(step_number: int) -> MigrationMetrics:
    """Create deterministic metrics for checkpoint flow tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=float(step_number),
        throughput_items_per_second=float(step_number),
        average_item_size=step_number * 100,
        processed_bytes=step_number * 1_000,
        estimated_remaining_seconds=None,
        peak_memory_usage_mb=None,
        total_items=step_number,
        processed_items=step_number,
        successful_items=step_number,
        failed_items=0,
        skipped_items=0,
        retried_items=0,
        uploaded_items=step_number,
        verification_failures=0,
        total_bytes=step_number * 1_000,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_report(step_number: int) -> ExecutionReport:
    """Create deterministic execution reports for checkpoint flow tests."""

    return ExecutionReport(
        successful_steps=1,
        failed_steps=0,
        skipped_steps=0,
        duration_seconds=float(step_number),
        completed=True,
        metrics=_build_metrics(step_number),
    )


class _RecordingCheckpointRepository(CheckpointRepositoryPort):
    """Keep checkpoint snapshots in memory and record every save."""

    def __init__(self) -> None:
        """Create an empty checkpoint repository test double."""

        self._checkpoints: dict[str, CheckpointSnapshot] = {}
        self.saved_checkpoints: list[CheckpointSnapshot] = []

    def save_checkpoint(self, checkpoint: CheckpointSnapshot) -> None:
        """Store a checkpoint snapshot and record the save order."""

        self.saved_checkpoints.append(checkpoint)
        self._checkpoints[checkpoint.migration_job_id] = checkpoint

    def load_checkpoint(self, migration_job_id: str) -> CheckpointSnapshot | None:
        """Load the latest checkpoint snapshot for a migration job."""

        return self._checkpoints.get(migration_job_id)

    def delete_checkpoint(self, migration_job_id: str) -> None:
        """Delete a checkpoint snapshot from the repository test double."""

        self._checkpoints.pop(migration_job_id, None)

    def checkpoint_exists(self, migration_job_id: str) -> bool:
        """Return whether a checkpoint exists for the supplied migration job."""

        return migration_job_id in self._checkpoints


class _DeterministicIdentifierGenerator(IdentifierGeneratorPort):
    """Return predictable identifiers for checkpoint flow tests."""

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

        return "migration-job-1"

    def next_migration_item_id(self) -> str:
        """Return a deterministic migration item identifier."""

        return "migration-item-1"


class _RecordingStep(PipelineStep):
    """Record lifecycle calls while returning a predefined report."""

    def __init__(self, report: ExecutionReport, *, fail_on_execute: bool = False) -> None:
        """Create a recording step with a deterministic report."""

        self._report = report
        self._fail_on_execute = fail_on_execute
        self.calls: list[str] = []

    def prepare(self, context: ExecutionContext) -> None:
        """Record step preparation."""

        state = context.state
        assert state is not None
        self.calls.append(f"prepare:{context.current_step}:{state.value}")

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Record step execution and optionally fail."""

        state = context.state
        assert state is not None
        self.calls.append(f"execute:{context.current_step}:{state.value}")
        if self._fail_on_execute:
            raise RuntimeError("checkpoint test failure")

        return self._report

    def finalize(self, context: ExecutionContext) -> None:
        """Record step finalization."""

        state = context.state
        assert state is not None
        self.calls.append(f"finalize:{context.current_step}:{state.value}")

    def rollback(self, context: ExecutionContext) -> None:
        """Record step rollback."""

        state = context.state
        assert state is not None
        self.calls.append(f"rollback:{context.current_step}:{state.value}")


class DiscoverArchivesStep(_RecordingStep):
    """Recording discovery step used to exercise the checkpoint flow."""


class ExtractItemsStep(_RecordingStep):
    """Recording extraction step used to exercise the checkpoint flow."""


class TransformItemsStep(_RecordingStep):
    """Recording transformation step used to exercise the checkpoint flow."""


class UploadItemsStep(_RecordingStep):
    """Recording upload step used to exercise the checkpoint flow."""


class VerifyItemsStep(_RecordingStep):
    """Recording verification step used to exercise the checkpoint flow."""


class FinalizeMigrationStep(_RecordingStep):
    """Recording finalization step used to exercise the checkpoint flow."""


def test_pipeline_runner_saves_checkpoints_after_each_successful_step() -> None:
    """The runner should persist a checkpoint after each successful step."""

    repository = _RecordingCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=repository)
    identifier_generator = _DeterministicIdentifierGenerator()
    discover_step = DiscoverArchivesStep(_build_report(1))
    extract_step = ExtractItemsStep(_build_report(2))
    transform_step = TransformItemsStep(_build_report(3))
    upload_step = UploadItemsStep(_build_report(4))
    verify_step = VerifyItemsStep(_build_report(5))
    finalize_step = FinalizeMigrationStep(_build_report(6))
    runner = PipelineRunner(
        [
            discover_step,
            extract_step,
            transform_step,
            upload_step,
            verify_step,
            finalize_step,
        ],
        checkpoint_service=checkpoint_service,
        identifier_generator=identifier_generator,
    )

    result = runner.run()

    assert result.success is True
    assert runner.checkpoint_service is checkpoint_service
    assert runner.execution_context is not None
    assert runner.execution_context.migration_id == "migration-job-1"
    assert len(repository.saved_checkpoints) == 6
    assert [checkpoint.last_completed_step for checkpoint in repository.saved_checkpoints] == [
        "DiscoverArchivesStep",
        "ExtractItemsStep",
        "TransformItemsStep",
        "UploadItemsStep",
        "VerifyItemsStep",
        "FinalizeMigrationStep",
    ]
    assert [checkpoint.current_state for checkpoint in repository.saved_checkpoints] == [
        MigrationState.DISCOVERING.value,
        MigrationState.EXTRACTING.value,
        MigrationState.TRANSFORMING.value,
        MigrationState.UPLOADING.value,
        MigrationState.VERIFYING.value,
        MigrationState.FINALIZING.value,
    ]
    assert repository.load_checkpoint("migration-job-1") == repository.saved_checkpoints[-1]
    assert runner.current_step_context is not None
    checkpoint = runner.current_step_context.checkpoint
    assert checkpoint == repository.saved_checkpoints[-1]
    assert checkpoint is not None
    assert checkpoint.processed_items == 6
    assert checkpoint.successful_items == 6
    assert checkpoint.failed_items == 0
    assert checkpoint.uploaded_items == 6
    assert checkpoint.verification_failures == 0
    assert checkpoint.version == 1
    assert runner.execution_result == result


def test_pipeline_runner_persists_filter_metadata_in_checkpoints() -> None:
    """The runner should store configured filters in persisted checkpoints."""

    repository = _RecordingCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=repository)
    identifier_generator = _DeterministicIdentifierGenerator()
    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    execution_context = ExecutionContext(
        migration_id="migration-job-1",
        configuration=MigrationConfiguration(
            archive_names=("Archive A1",),
            folder_paths=("/Inbox",),
            start_date=started_at,
            end_date=started_at,
        ),
        started_at=started_at,
        current_step=None,
        metrics=_build_metrics(1),
        progress_tracker=ProgressTracker(
            snapshot=ProgressSnapshot(
                total_items=1,
                processed_items=1,
                successful_items=1,
                failed_items=0,
                skipped_items=0,
                current_archive=None,
                current_mailbox=None,
                current_item=None,
                started_at=started_at,
                last_updated=started_at,
            ),
            metrics=_build_metrics(1),
        ),
        state=MigrationState.INITIALIZING,
        current_timestamp=started_at,
    )
    initial_context = MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=execution_context.progress_tracker,
        state_machine=None,
        execution_report=None,
    )
    runner = PipelineRunner(
        [DiscoverArchivesStep(_build_report(1))],
        checkpoint_service=checkpoint_service,
        identifier_generator=identifier_generator,
        initial_context=initial_context,
    )

    runner.run()

    checkpoint = repository.saved_checkpoints[-1]
    assert checkpoint.archive_names == ("Archive A1",)
    assert checkpoint.folder_paths == ("/Inbox",)
    assert checkpoint.start_date == started_at
    assert checkpoint.end_date == started_at


def test_pipeline_runner_keeps_previous_checkpoint_after_later_failure() -> None:
    """The runner should preserve the last successful checkpoint on failure."""

    repository = _RecordingCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=repository)
    discover_step = DiscoverArchivesStep(_build_report(1))
    upload_step = UploadItemsStep(_build_report(2), fail_on_execute=True)
    runner = PipelineRunner(
        [
            discover_step,
            upload_step,
        ],
        checkpoint_service=checkpoint_service,
    )

    result = runner.run()

    assert result.success is False
    assert len(repository.saved_checkpoints) == 1
    assert repository.saved_checkpoints[0].last_completed_step == "DiscoverArchivesStep"
    assert repository.load_checkpoint(repository.saved_checkpoints[0].migration_job_id) == (
        repository.saved_checkpoints[0]
    )
    assert runner.current_step_context is not None
    checkpoint = runner.current_step_context.checkpoint
    assert checkpoint == repository.saved_checkpoints[0]
    assert checkpoint is not None
    assert checkpoint.current_state == MigrationState.DISCOVERING.value
    assert runner.current_step_context.execution_result is None
    assert any(call.startswith("rollback:UploadItemsStep:failed") for call in upload_step.calls)


def test_pipeline_runner_remains_compatible_without_checkpoint_service() -> None:
    """The runner should continue working when checkpointing is disabled."""

    runner = PipelineRunner([DiscoverArchivesStep(_build_report(1))])

    result = runner.run()

    assert result.success is True
    assert runner.current_step_context is not None
    assert runner.current_step_context.checkpoint is None


def test_pipeline_runner_does_not_import_concrete_checkpoint_repository() -> None:
    """The runner must stay decoupled from concrete checkpoint repositories."""

    source_text = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "migration_engine"
        / "runner"
        / "pipeline_runner.py"
    ).read_text()

    assert "InMemoryCheckpointRepository" not in source_text
    assert "CheckpointService" in source_text


def test_pipeline_runner_checkpoint_contract_stays_serializable_and_minimal() -> None:
    """Checkpoint snapshots should remain target-neutral and payload-free."""

    repository = _RecordingCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=repository)
    runner = PipelineRunner(
        [DiscoverArchivesStep(_build_report(1))],
        checkpoint_service=checkpoint_service,
    )

    runner.run()
    checkpoint = repository.saved_checkpoints[-1]

    assert isinstance(checkpoint, CheckpointSnapshot)
    assert {field.name for field in fields(checkpoint)} == {
        "checkpoint_id",
        "migration_job_id",
        "last_completed_step",
        "last_processed_item_id",
        "processed_items",
        "successful_items",
        "failed_items",
        "skipped_items",
        "filtered_archives",
        "filtered_items",
        "uploaded_items",
        "verification_failures",
        "current_state",
        "created_at",
        "updated_at",
        "dry_run",
        "dry_run_items",
        "archive_names",
        "folder_paths",
        "start_date",
        "end_date",
        "version",
    }
    assert all(
        prohibited not in field.name
        for field in fields(checkpoint)
        for prohibited in ("body", "payload", "service", "adapter", "token", "secret")
    )
    assert checkpoint.last_processed_item_id is None
    assert checkpoint.current_state == MigrationState.DISCOVERING.value
    assert checkpoint.created_at is not None
    assert checkpoint.updated_at is not None
    assert checkpoint.updated_at >= checkpoint.created_at
