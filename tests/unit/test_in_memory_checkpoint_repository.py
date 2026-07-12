"""Regression tests for the in-memory checkpoint repository adapter."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from adapters.database import InMemoryCheckpointRepository
from application.services import CheckpointService
from migration_engine.checkpoint import CheckpointSnapshot
from ports import CheckpointRepositoryPort


def _build_checkpoint_snapshot(
    *,
    checkpoint_id: str = "checkpoint-1",
    migration_job_id: str = "job-1",
    last_completed_step: str = "UploadItemsStep",
    last_processed_item_id: str = "item-1",
) -> CheckpointSnapshot:
    """Create a deterministic checkpoint snapshot for repository tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return CheckpointSnapshot(
        checkpoint_id=checkpoint_id,
        migration_job_id=migration_job_id,
        last_completed_step=last_completed_step,
        last_processed_item_id=last_processed_item_id,
        processed_items=3,
        successful_items=2,
        failed_items=1,
        skipped_items=0,
        uploaded_items=2,
        verification_failures=1,
        current_state="verifying",
        created_at=timestamp,
        updated_at=timestamp,
        version=1,
    )


def test_in_memory_checkpoint_repository_satisfies_repository_port() -> None:
    """The concrete repository should implement the checkpoint repository port."""

    repository = InMemoryCheckpointRepository()

    assert isinstance(repository, CheckpointRepositoryPort)


def test_in_memory_checkpoint_repository_saves_loads_and_overwrites_checkpoints() -> None:
    """The repository should save, load, and replace checkpoints deterministically."""

    repository = InMemoryCheckpointRepository()
    first_checkpoint = _build_checkpoint_snapshot(
        checkpoint_id="checkpoint-1",
        migration_job_id="job-1",
        last_processed_item_id="item-1",
    )
    second_checkpoint = _build_checkpoint_snapshot(
        checkpoint_id="checkpoint-2",
        migration_job_id="job-1",
        last_completed_step="FinalizeMigrationStep",
        last_processed_item_id="item-2",
    )
    other_checkpoint = _build_checkpoint_snapshot(
        checkpoint_id="checkpoint-3",
        migration_job_id="job-2",
        last_processed_item_id="item-3",
    )

    assert repository.load_checkpoint("job-1") is None
    assert repository.checkpoint_exists("job-1") is False

    repository.save_checkpoint(first_checkpoint)
    assert repository.load_checkpoint("job-1") is first_checkpoint
    assert repository.checkpoint_exists("job-1") is True

    repository.save_checkpoint(second_checkpoint)
    assert repository.load_checkpoint("job-1") is second_checkpoint
    assert repository.load_checkpoint("job-2") is None

    repository.save(other_checkpoint)
    assert repository.get_by_job_id("job-2") is other_checkpoint
    assert repository.load_checkpoint("job-2") is other_checkpoint


def test_in_memory_checkpoint_repository_deletes_checkpoints_idempotently() -> None:
    """The repository should delete checkpoints without failing when absent."""

    repository = InMemoryCheckpointRepository()
    checkpoint = _build_checkpoint_snapshot()

    repository.delete_checkpoint(checkpoint.migration_job_id)
    assert repository.load_checkpoint(checkpoint.migration_job_id) is None
    assert repository.checkpoint_exists(checkpoint.migration_job_id) is False

    repository.save_checkpoint(checkpoint)
    assert repository.checkpoint_exists(checkpoint.migration_job_id) is True

    repository.delete_checkpoint(checkpoint.migration_job_id)
    assert repository.load_checkpoint(checkpoint.migration_job_id) is None
    assert repository.checkpoint_exists(checkpoint.migration_job_id) is False


def test_in_memory_checkpoint_repository_preserves_immutable_snapshots() -> None:
    """The repository should store and return immutable checkpoint snapshots."""

    repository = InMemoryCheckpointRepository()
    checkpoint = _build_checkpoint_snapshot()

    repository.save_checkpoint(checkpoint)
    loaded_checkpoint = repository.load_checkpoint(checkpoint.migration_job_id)

    assert loaded_checkpoint is checkpoint
    assert loaded_checkpoint == checkpoint
    with pytest.raises(FrozenInstanceError):
        checkpoint.current_state = "completed"  # type: ignore[misc]


def test_in_memory_checkpoint_repository_keeps_state_private_and_isolated() -> None:
    """The repository should not expose internal storage or orchestration behavior."""

    repository = InMemoryCheckpointRepository()
    first_checkpoint = _build_checkpoint_snapshot(
        checkpoint_id="checkpoint-1",
        migration_job_id="job-1",
    )
    second_checkpoint = _build_checkpoint_snapshot(
        checkpoint_id="checkpoint-2",
        migration_job_id="job-2",
        last_completed_step="FinalizeMigrationStep",
    )

    repository.save_checkpoint(first_checkpoint)
    repository.save_checkpoint(second_checkpoint)

    assert not hasattr(repository, "checkpoints")
    assert not hasattr(repository, "storage")
    assert not hasattr(repository, "run")
    assert not hasattr(repository, "execute")
    assert not hasattr(repository, "prepare")
    assert not hasattr(repository, "rollback")
    assert not hasattr(repository, "finalize")

    with pytest.raises(AttributeError):
        _ = repository.checkpoints  # type: ignore[attr-defined]

    source_text = inspect.getsource(InMemoryCheckpointRepository)
    for forbidden_marker in (
        "PipelineRunner",
        "MigrationStepContext",
        "mock_ev",
        "mock_storionx",
        "session",
        "upload",
        "verification",
    ):
        assert forbidden_marker not in source_text

    assert repository.load_checkpoint("job-1") is first_checkpoint
    assert repository.load_checkpoint("job-2") is second_checkpoint


def test_checkpoint_service_works_with_concrete_repository() -> None:
    """The checkpoint service should coordinate correctly with the concrete repository."""

    repository = InMemoryCheckpointRepository()
    service = CheckpointService(checkpoint_repository=repository)
    checkpoint = _build_checkpoint_snapshot(
        checkpoint_id="checkpoint-9",
        migration_job_id="job-9",
        last_processed_item_id="item-9",
    )

    service.save_checkpoint(checkpoint)
    assert service.checkpoint_exists("job-9") is True
    assert service.load_checkpoint("job-9") is checkpoint

    service.delete_checkpoint("job-9")
    assert service.checkpoint_exists("job-9") is False
    assert service.load_checkpoint("job-9") is None
