"""Regression tests for the archive discovery migration step."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from migration_engine.discovery import ArchiveDiscoveryResult
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import DiscoverArchivesStep
from mock_ev.entities import Archive, VaultStore
from mock_ev.generators import DatasetGenerator


def _build_vault_store(name: str, archive_names: tuple[str, ...]) -> VaultStore:
    """Create a mock vault store with the requested archives."""

    return VaultStore(
        name=name,
        archives=[Archive(name=archive_name) for archive_name in archive_names],
    )


def _build_metrics() -> MigrationMetrics:
    """Create a sample metrics object for discovery tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=9.5,
        throughput_items_per_second=1.25,
        average_item_size=512,
        processed_bytes=1_024,
        estimated_remaining_seconds=3.0,
        peak_memory_usage_mb=64.0,
        total_items=7,
        processed_items=3,
        successful_items=2,
        failed_items=1,
        skipped_items=1,
        retried_items=0,
        uploaded_items=0,
        verification_failures=1,
        total_bytes=2_048,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_snapshot() -> ProgressSnapshot:
    """Create a sample progress snapshot for discovery tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=7,
        processed_items=3,
        successful_items=2,
        failed_items=1,
        skipped_items=1,
        current_archive="seed-archive",
        current_mailbox=None,
        current_item=None,
        started_at=timestamp,
        last_updated=timestamp,
    )


def _build_step_context(
    *,
    current_timestamp: datetime,
    state: MigrationState,
    tracker: ProgressTracker | None = None,
    report: ExecutionReport | None = None,
) -> MigrationStepContext:
    """Create a migration step context for discovery tests."""

    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        current_step=None,
        metrics=_build_metrics(),
        progress_tracker=tracker,
        state=state,
        current_timestamp=current_timestamp,
    )
    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=tracker,
        state_machine=MigrationStateMachine(current_state=state),
        execution_report=report,
    )


def test_discover_archives_step_updates_context_and_orchestration_state() -> None:
    """The step should discover archives and update shared orchestration state."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    discovered_at = started_at + timedelta(seconds=4)
    metrics = _build_metrics()
    snapshot = _build_snapshot()
    tracker = ProgressTracker(snapshot=snapshot, metrics=metrics)
    context = _build_step_context(
        current_timestamp=discovered_at,
        state=MigrationState.INITIALIZING,
        tracker=tracker,
    )
    vault_stores = (
        _build_vault_store("Vault Store A", ("Archive A1", "Archive A2")),
        _build_vault_store("Vault Store B", ("Archive B1",)),
    )

    step = DiscoverArchivesStep(vault_stores=vault_stores)
    updated_context = step.discover(context)

    expected_result = ArchiveDiscoveryResult(
        vault_store_names=("Vault Store A", "Vault Store B"),
        archive_names=("Archive A1", "Archive A2", "Archive B1"),
        vault_store_count=2,
        archive_count=3,
    )

    assert updated_context.discovery_result == expected_result
    assert updated_context.execution_context.current_step == "DiscoverArchivesStep"
    assert updated_context.execution_context.state == MigrationState.DISCOVERING
    assert updated_context.execution_context.current_timestamp == discovered_at
    assert updated_context.state_machine is context.state_machine
    assert updated_context.state_machine is not None
    assert updated_context.state_machine.current_state == MigrationState.DISCOVERING
    assert updated_context.progress_tracker is tracker
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.completed is True
    assert updated_context.execution_report.successful_steps == 1
    assert updated_context.execution_report.failed_steps == 0
    assert updated_context.execution_report.skipped_steps == 0
    assert updated_context.execution_report.metrics == updated_context.execution_context.metrics
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.duration_seconds == 4.0
    assert updated_context.execution_context.metrics.throughput_items_per_second == 0.75
    assert updated_context.execution_context.metrics.total_items == 3
    assert updated_context.execution_context.metrics.processed_items == 3
    assert updated_context.execution_context.metrics.successful_items == 3
    assert updated_context.execution_context.metrics.failed_items == 0
    assert updated_context.execution_context.metrics.skipped_items == 0
    assert updated_context.execution_context.metrics.retried_items == 0
    assert updated_context.execution_context.metrics.uploaded_items == 0
    assert updated_context.execution_context.metrics.verification_failures == 0
    assert updated_context.execution_context.metrics.processed_bytes == metrics.processed_bytes
    assert updated_context.execution_context.metrics.total_bytes == metrics.total_bytes
    assert updated_context.execution_context.metrics.started_at == started_at
    assert updated_context.execution_context.metrics.finished_at == discovered_at
    assert tracker.current_snapshot.total_items == 3
    assert tracker.current_snapshot.processed_items == 3
    assert tracker.current_snapshot.successful_items == 3
    assert tracker.current_snapshot.failed_items == 0
    assert tracker.current_snapshot.skipped_items == 0
    assert tracker.current_snapshot.current_archive == "Archive A1"
    assert tracker.current_migration_state == MigrationState.DISCOVERING
    assert tracker.current_execution_context is updated_context.execution_context
    assert tracker.current_execution_report is updated_context.execution_report
    assert updated_context.vault_stores == vault_stores


def test_discover_archives_step_handles_empty_vault() -> None:
    """The step should handle an empty mock vault without failing."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    discovered_at = started_at + timedelta(seconds=1)
    tracker = ProgressTracker(snapshot=_build_snapshot(), metrics=_build_metrics())
    context = _build_step_context(
        current_timestamp=discovered_at,
        state=MigrationState.INITIALIZING,
        tracker=tracker,
    )

    step = DiscoverArchivesStep(vault_stores=())
    updated_context = step.discover(context)

    assert updated_context.discovery_result == ArchiveDiscoveryResult(
        vault_store_names=(),
        archive_names=(),
        vault_store_count=0,
        archive_count=0,
    )
    assert updated_context.execution_report is not None
    assert updated_context.execution_report.completed is True
    assert updated_context.execution_report.successful_steps == 1
    assert updated_context.execution_context.metrics is not None
    assert updated_context.execution_context.metrics.total_items == 0
    assert updated_context.execution_context.metrics.processed_items == 0
    assert updated_context.execution_context.metrics.successful_items == 0
    assert updated_context.execution_context.metrics.failed_items == 0
    assert updated_context.execution_context.metrics.skipped_items == 0
    assert tracker.current_snapshot.total_items == 0
    assert tracker.current_snapshot.processed_items == 0
    assert tracker.current_snapshot.successful_items == 0
    assert tracker.current_snapshot.failed_items == 0
    assert tracker.current_snapshot.skipped_items == 0
    assert tracker.current_snapshot.current_archive is None


def test_discover_archives_step_is_deterministic_for_default_generation() -> None:
    """The default mock Enterprise Vault generation should be deterministic."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    discovered_at = started_at + timedelta(seconds=2)
    first_context = _build_step_context(
        current_timestamp=discovered_at,
        state=MigrationState.INITIALIZING,
    )
    second_context = _build_step_context(
        current_timestamp=discovered_at,
        state=MigrationState.INITIALIZING,
    )

    first_step = DiscoverArchivesStep(dataset_generator=DatasetGenerator(seed=0))
    second_step = DiscoverArchivesStep(dataset_generator=DatasetGenerator(seed=0))

    first_result = first_step.discover(first_context)
    second_result = second_step.discover(second_context)

    assert first_result.discovery_result == second_result.discovery_result
    assert first_result.execution_report == second_result.execution_report
    assert first_result.execution_context.metrics == second_result.execution_context.metrics
