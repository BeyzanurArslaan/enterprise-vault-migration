"""Regression tests for the checkpoint repository port and service."""

from __future__ import annotations

from datetime import UTC, datetime

from application.services import CheckpointService
from migration_engine.checkpoint import CheckpointSnapshot
from ports import CheckpointRepositoryPort


class _InMemoryCheckpointRepository(CheckpointRepositoryPort):
    """Store checkpoints in memory for contract verification."""

    def __init__(self) -> None:
        """Create an in-memory checkpoint repository."""

        self._checkpoints: dict[str, CheckpointSnapshot] = {}

    def save_checkpoint(self, checkpoint: CheckpointSnapshot) -> None:
        """Persist a checkpoint snapshot in memory."""

        self._checkpoints[checkpoint.migration_job_id] = checkpoint

    def load_checkpoint(self, migration_job_id: str) -> CheckpointSnapshot | None:
        """Load a checkpoint snapshot from memory."""

        return self._checkpoints.get(migration_job_id)

    def delete_checkpoint(self, migration_job_id: str) -> None:
        """Delete a checkpoint snapshot from memory."""

        self._checkpoints.pop(migration_job_id, None)

    def checkpoint_exists(self, migration_job_id: str) -> bool:
        """Return whether a checkpoint snapshot exists."""

        return migration_job_id in self._checkpoints


def _build_checkpoint_snapshot(
    *,
    checkpoint_id: str = "checkpoint-1",
    migration_job_id: str = "job-1",
) -> CheckpointSnapshot:
    """Create a deterministic checkpoint snapshot for repository tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return CheckpointSnapshot(
        checkpoint_id=checkpoint_id,
        migration_job_id=migration_job_id,
        last_completed_step="UploadItemsStep",
        last_processed_item_id="item-1",
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


def test_checkpoint_repository_port_supports_aliases_and_primary_methods() -> None:
    """The repository port should expose both primary and legacy method names."""

    repository = _InMemoryCheckpointRepository()
    checkpoint = _build_checkpoint_snapshot()

    repository.save_checkpoint(checkpoint)
    assert repository.checkpoint_exists(checkpoint.migration_job_id) is True
    assert repository.load_checkpoint(checkpoint.migration_job_id) == checkpoint

    repository.save(checkpoint)
    assert repository.get_by_job_id(checkpoint.migration_job_id) == checkpoint

    repository.delete_checkpoint(checkpoint.migration_job_id)
    assert repository.checkpoint_exists(checkpoint.migration_job_id) is False
    assert repository.load_checkpoint(checkpoint.migration_job_id) is None


def test_checkpoint_service_coordinates_through_repository_port() -> None:
    """The checkpoint service should delegate to the repository port only."""

    repository = _InMemoryCheckpointRepository()
    service = CheckpointService(checkpoint_repository=repository)
    checkpoint = _build_checkpoint_snapshot(checkpoint_id="checkpoint-2", migration_job_id="job-2")

    service.save_checkpoint(checkpoint)

    assert service.checkpoint_exists("job-2") is True
    assert service.load_checkpoint("job-2") == checkpoint

    service.delete_checkpoint("job-2")
    assert service.checkpoint_exists("job-2") is False
    assert service.load_checkpoint("job-2") is None
