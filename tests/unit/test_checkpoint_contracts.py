"""Regression tests for checkpoint contracts and engine context flow."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from migration_engine.checkpoint import CheckpointSnapshot
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ProgressSnapshot
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext


def _build_checkpoint_snapshot() -> CheckpointSnapshot:
    """Create a deterministic checkpoint snapshot for contract tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return CheckpointSnapshot(
        checkpoint_id="checkpoint-1",
        migration_job_id="job-1",
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
        dry_run=False,
        dry_run_items=0,
        version=1,
    )


def _build_execution_context() -> ExecutionContext:
    """Create a deterministic execution context for checkpoint tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    snapshot = ProgressSnapshot(
        total_items=3,
        processed_items=3,
        successful_items=2,
        failed_items=1,
        skipped_items=0,
        current_archive="Archive One",
        current_mailbox="alice@example.com",
        current_item="Quarterly Report.eml",
        started_at=timestamp,
        last_updated=timestamp,
    )
    tracker = ProgressTracker(snapshot=snapshot, migration_state=MigrationState.UPLOADING)
    metrics = MigrationMetrics(
        duration_seconds=5.0,
        throughput_items_per_second=1.0,
        average_item_size=256,
        processed_bytes=768,
        estimated_remaining_seconds=None,
        peak_memory_usage_mb=None,
        total_items=3,
        processed_items=3,
        successful_items=2,
        failed_items=1,
        skipped_items=0,
        retried_items=0,
        uploaded_items=2,
        verification_failures=1,
        total_bytes=768,
        started_at=timestamp,
        finished_at=timestamp,
    )
    return ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=timestamp,
        current_step="upload",
        metrics=metrics,
        progress_tracker=tracker,
        state=MigrationState.UPLOADING,
        current_timestamp=timestamp,
    )


def test_checkpoint_snapshot_is_immutable_and_versioned() -> None:
    """Checkpoint snapshots should be frozen and carry a schema version."""

    checkpoint = _build_checkpoint_snapshot()

    assert checkpoint.version == 1
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

    with pytest.raises(FrozenInstanceError):
        checkpoint.version = 2  # type: ignore[misc]

    updated_checkpoint = replace(checkpoint, updated_at=checkpoint.updated_at)
    assert updated_checkpoint == checkpoint


def test_checkpoint_snapshot_uses_serializable_safe_field_types() -> None:
    """Checkpoint snapshots should keep only serializable-safe continuation data."""

    checkpoint = _build_checkpoint_snapshot()

    assert isinstance(checkpoint.checkpoint_id, str)
    assert isinstance(checkpoint.migration_job_id, str)
    assert isinstance(checkpoint.last_completed_step, str)
    assert isinstance(checkpoint.last_processed_item_id, str)
    assert isinstance(checkpoint.processed_items, int)
    assert isinstance(checkpoint.successful_items, int)
    assert isinstance(checkpoint.failed_items, int)
    assert isinstance(checkpoint.skipped_items, int)
    assert isinstance(checkpoint.uploaded_items, int)
    assert isinstance(checkpoint.verification_failures, int)
    assert isinstance(checkpoint.current_state, str)
    assert isinstance(checkpoint.created_at, datetime)
    assert isinstance(checkpoint.updated_at, datetime)
    assert isinstance(checkpoint.dry_run, bool)
    assert isinstance(checkpoint.dry_run_items, int)
    assert isinstance(checkpoint.filtered_archives, int)
    assert isinstance(checkpoint.filtered_items, int)
    assert checkpoint.archive_names is None
    assert checkpoint.folder_paths is None
    assert checkpoint.start_date is None
    assert checkpoint.end_date is None
    assert checkpoint.dry_run is False
    assert checkpoint.dry_run_items == 0

    assert not any(
        forbidden in {field.name for field in fields(checkpoint)}
        for forbidden in {
            "body",
            "attachments",
            "content",
            "payload",
            "service",
            "adapter",
            "token",
            "secret",
            "credentials",
        }
    )


def test_migration_step_context_can_carry_optional_checkpoint() -> None:
    """Migration step contexts should accept an optional checkpoint snapshot."""

    execution_context = _build_execution_context()
    checkpoint = _build_checkpoint_snapshot()

    context = MigrationStepContext(
        execution_context=execution_context,
        state_machine=MigrationStateMachine(current_state=MigrationState.UPLOADING),
        checkpoint=checkpoint,
    )

    assert context.checkpoint == checkpoint
    assert context.execution_context == execution_context
    assert replace(context, checkpoint=None).checkpoint is None
    assert MigrationStepContext(execution_context=execution_context).checkpoint is None


def test_checkpoint_contracts_do_not_import_infrastructure() -> None:
    """Checkpoint contracts should stay free of infrastructure coupling."""

    checkpoint_modules = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "migration_engine"
        / "checkpoint"
        / "__init__.py",
        Path(__file__).resolve().parents[2]
        / "src"
        / "migration_engine"
        / "checkpoint"
        / "checkpoint_snapshot.py",
        Path(__file__).resolve().parents[2] / "src" / "migration_engine" / "step_context.py",
        Path(__file__).resolve().parents[2]
        / "src"
        / "application"
        / "services"
        / "checkpoint_service.py",
        Path(__file__).resolve().parents[2] / "src" / "ports" / "checkpoint_repository_port.py",
    )

    forbidden_markers = (
        "mock_ev",
        "mock_storionx",
        "sqlalchemy",
        "sqlite3",
        "fastapi",
    )
    for module_path in checkpoint_modules:
        source_text = module_path.read_text()
        assert not any(marker in source_text for marker in forbidden_markers)

    assert (
        "CheckpointSnapshot"
        in Path(__file__)
        .resolve()
        .parents[2]
        .joinpath("src/migration_engine/checkpoint/checkpoint_snapshot.py")
        .read_text()
    )
