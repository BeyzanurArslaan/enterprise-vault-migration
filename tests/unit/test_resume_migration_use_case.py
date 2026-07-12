"""Regression tests for the resume migration application use case."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from adapters.database import InMemoryCheckpointRepository
from application.commands import ResumeMigrationCommand
from application.services import CheckpointService
from application.use_cases.resume_migration import ResumeMigrationUseCase
from domain.exceptions import (
    CheckpointNotFoundError,
    NonResumableCheckpointError,
    UnsupportedCheckpointVersionError,
)
from domain.value_objects.identifiers import MigrationJobId
from migration_engine.checkpoint import CheckpointSnapshot
from migration_engine.execution_result import ExecutionResult
from migration_engine.orchestrator import MigrationOrchestrator
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState

TEST_JOB_ID = UUID("12345678-1234-5678-1234-567812345678")


def _build_checkpoint_snapshot(
    *,
    version: int = 1,
    current_state: str = MigrationState.VERIFYING.value,
    job_id: str = str(TEST_JOB_ID),
) -> CheckpointSnapshot:
    """Create a deterministic checkpoint snapshot for resume tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return CheckpointSnapshot(
        checkpoint_id="checkpoint-1",
        migration_job_id=job_id,
        last_completed_step="VerifyItemsStep",
        last_processed_item_id="message-1",
        processed_items=3,
        successful_items=3,
        failed_items=0,
        skipped_items=0,
        uploaded_items=3,
        verification_failures=0,
        current_state=current_state,
        created_at=timestamp,
        updated_at=timestamp,
        version=version,
    )


class _RecordingRunner(PipelineRunner):
    """Record checkpoint resume calls without executing a real workflow."""

    def __init__(self) -> None:
        """Create a recording runner for use-case delegation tests."""

        super().__init__(())
        self.run_calls = 0
        self.resume_checkpoint: CheckpointSnapshot | None = None
        self.result = ExecutionResult(success=True, warnings=("delegated",))

    def run(
        self,
        *,
        resume_checkpoint: CheckpointSnapshot | None = None,
    ) -> ExecutionResult:
        """Record the checkpoint argument and return the configured result."""

        self.run_calls += 1
        self.resume_checkpoint = resume_checkpoint
        return self.result


def _build_command() -> ResumeMigrationCommand:
    """Create a deterministic resume command for use-case tests."""

    return ResumeMigrationCommand(job_id=MigrationJobId(TEST_JOB_ID))


def test_resume_migration_use_case_loads_checkpoint_and_delegates() -> None:
    """The use case should load a checkpoint and delegate execution."""

    repository = InMemoryCheckpointRepository()
    checkpoint = _build_checkpoint_snapshot()
    repository.save_checkpoint(checkpoint)
    checkpoint_service = CheckpointService(checkpoint_repository=repository)
    runner = _RecordingRunner()
    orchestrator = MigrationOrchestrator(runner=runner)
    use_case = ResumeMigrationUseCase(
        checkpoint_service=checkpoint_service,
        migration_orchestrator=orchestrator,
    )

    result = use_case.execute(_build_command())

    assert result is runner.result
    assert runner.run_calls == 1
    assert runner.resume_checkpoint == checkpoint


def test_resume_migration_use_case_raises_when_checkpoint_is_missing() -> None:
    """The use case should fail structurally when no checkpoint exists."""

    checkpoint_service = CheckpointService(
        checkpoint_repository=InMemoryCheckpointRepository(),
    )
    use_case = ResumeMigrationUseCase(
        checkpoint_service=checkpoint_service,
        migration_orchestrator=MigrationOrchestrator(runner=_RecordingRunner()),
    )

    with pytest.raises(CheckpointNotFoundError):
        use_case.execute(ResumeMigrationCommand(job_id=MigrationJobId(uuid4())))


def test_resume_migration_use_case_rejects_unsupported_checkpoint_version() -> None:
    """The use case should reject checkpoints with unsupported versions."""

    repository = InMemoryCheckpointRepository()
    checkpoint = _build_checkpoint_snapshot(version=2)
    repository.save_checkpoint(checkpoint)
    use_case = ResumeMigrationUseCase(
        checkpoint_service=CheckpointService(checkpoint_repository=repository),
        migration_orchestrator=MigrationOrchestrator(runner=_RecordingRunner()),
    )

    with pytest.raises(UnsupportedCheckpointVersionError):
        use_case.execute(_build_command())


@pytest.mark.parametrize(
    "current_state",
    [MigrationState.COMPLETED.value, MigrationState.CANCELLED.value],
)
def test_resume_migration_use_case_rejects_terminal_checkpoints(
    current_state: str,
) -> None:
    """Terminal checkpoints should not resume without a supported force path."""

    repository = InMemoryCheckpointRepository()
    checkpoint = _build_checkpoint_snapshot(current_state=current_state)
    repository.save_checkpoint(checkpoint)
    use_case = ResumeMigrationUseCase(
        checkpoint_service=CheckpointService(checkpoint_repository=repository),
        migration_orchestrator=MigrationOrchestrator(runner=_RecordingRunner()),
    )

    with pytest.raises(NonResumableCheckpointError):
        use_case.execute(_build_command())


def test_resume_migration_use_case_module_stays_free_of_infrastructure_imports() -> None:
    """The use case module should stay decoupled from concrete adapters."""

    source_text = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "application"
        / "use_cases"
        / "resume_migration.py"
    ).read_text()
    assert "mock_storionx" not in source_text
    assert "InMemoryCheckpointRepository" not in source_text
