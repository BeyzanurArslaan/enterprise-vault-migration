"""Discover archives pipeline step module.

This module defines the first executable migration step responsible for
discovering available Enterprise Vault vault stores and archives. The step
only performs structural discovery and updates shared orchestration state.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from ..configuration import MigrationConfiguration
from ..contracts import (
    ExecutionContext,
    ExecutionReport,
    PipelineStep,
    ProgressSnapshot,
    SourceDatasetGenerator,
    SourceVaultStore,
)
from ..discovery import ArchiveDiscoveryResult
from ..metrics import MigrationMetrics
from ..progress_tracker import ProgressTracker
from ..state_machine import MigrationState, MigrationStateMachine
from ..step_context import MigrationStepContext


class DiscoverArchivesStep(PipelineStep):
    """Discover Enterprise Vault vault stores and archive structures."""

    def __init__(
        self,
        *,
        vault_stores: Sequence[SourceVaultStore] | None = None,
        dataset_generator: SourceDatasetGenerator | None = None,
    ) -> None:
        """Create a discovery step with optional deterministic data overrides."""

        self._vault_stores = tuple(vault_stores) if vault_stores is not None else None
        self._dataset_generator = dataset_generator

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare archive discovery for the current migration context."""

        return None

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute archive discovery for the current migration context."""

        updated_context = self.discover(self._build_step_context(context))
        if updated_context.execution_report is None:
            message = "Archive discovery did not produce an execution report"
            raise RuntimeError(message)

        return updated_context.execution_report

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize archive discovery after execution."""

        return None

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback archive discovery after failure."""

        return None

    def discover(self, context: MigrationStepContext) -> MigrationStepContext:
        """Discover vault stores and archives within the mock Enterprise Vault."""

        started_at = context.execution_context.started_at
        discovered_at = context.execution_context.current_timestamp or started_at
        vault_stores = self._resolve_vault_stores()
        discovery_result = self._build_discovery_result(vault_stores)
        configuration = context.execution_context.configuration
        filtered_archives = 0
        archive_names = discovery_result.archive_names
        if configuration.archive_names is not None:
            allowed_archive_names = set(configuration.archive_names)
            archive_names = tuple(
                archive_name
                for archive_name in discovery_result.archive_names
                if archive_name in allowed_archive_names
            )
            filtered_archives = len(discovery_result.archive_names) - len(archive_names)

        discovery_result = ArchiveDiscoveryResult(
            vault_store_names=discovery_result.vault_store_names,
            archive_names=archive_names,
            vault_store_count=discovery_result.vault_store_count,
            archive_count=len(archive_names),
        )
        updated_state = self._resolve_state(context.state_machine)
        updated_metrics = self._resolve_metrics(
            metrics=(
                context.execution_context.metrics
                or (
                    context.progress_tracker.current_metrics
                    if context.progress_tracker is not None
                    else None
                )
            ),
            discovery_result=discovery_result,
            filtered_archives=filtered_archives,
            started_at=started_at,
            discovered_at=discovered_at,
        )
        updated_snapshot = self._build_snapshot(
            discovery_result=discovery_result,
            started_at=started_at,
            discovered_at=discovered_at,
        )
        updated_report = self._resolve_report(
            report=(
                context.execution_report
                or (
                    context.progress_tracker.current_execution_report
                    if context.progress_tracker is not None
                    else None
                )
            ),
            metrics=updated_metrics,
            configuration=configuration,
            started_at=started_at,
            discovered_at=discovered_at,
        )
        progress_tracker = self._resolve_tracker(
            tracker=context.progress_tracker,
            snapshot=updated_snapshot,
            metrics=updated_metrics,
            report=updated_report,
            migration_state=updated_state,
        )
        execution_context = replace(
            context.execution_context,
            current_step=self.__class__.__name__,
            metrics=updated_metrics,
            progress_tracker=progress_tracker,
            state=updated_state,
            current_timestamp=discovered_at,
        )
        progress_tracker.update_execution_context(execution_context)
        progress_tracker.update_execution_report(updated_report)
        progress_tracker.update_metrics(updated_metrics)
        progress_tracker.update_snapshot(updated_snapshot)
        progress_tracker.update_migration_state(updated_state)

        return replace(
            context,
            execution_context=execution_context,
            progress_tracker=progress_tracker,
            state_machine=context.state_machine,
            execution_report=updated_report,
            discovery_result=discovery_result,
            vault_stores=vault_stores,
        )

    def _build_step_context(self, context: ExecutionContext) -> MigrationStepContext:
        """Wrap a legacy execution context in a migration step context."""

        return MigrationStepContext(
            execution_context=context,
            progress_tracker=context.progress_tracker,
            state_machine=None,
            execution_report=None,
        )

    def _resolve_vault_stores(self) -> tuple[SourceVaultStore, ...]:
        """Return the vault stores that should be inspected for discovery."""

        if self._vault_stores is not None:
            return self._vault_stores

        if self._dataset_generator is not None:
            return tuple(self._dataset_generator.generate_small())

        return ()

    def _build_discovery_result(
        self,
        vault_stores: Sequence[SourceVaultStore],
    ) -> ArchiveDiscoveryResult:
        """Create a lightweight summary of discovered vault stores and archives."""

        vault_store_names = tuple(store.name for store in vault_stores)
        archive_names = tuple(archive.name for store in vault_stores for archive in store.archives)
        return ArchiveDiscoveryResult(
            vault_store_names=vault_store_names,
            archive_names=archive_names,
            vault_store_count=len(vault_store_names),
            archive_count=len(archive_names),
        )

    def _build_snapshot(
        self,
        *,
        discovery_result: ArchiveDiscoveryResult,
        started_at: datetime,
        discovered_at: datetime,
    ) -> ProgressSnapshot:
        """Build the updated progress snapshot for discovery bookkeeping."""

        current_archive = (
            discovery_result.archive_names[0] if discovery_result.archive_names else None
        )
        return ProgressSnapshot(
            total_items=discovery_result.archive_count,
            processed_items=discovery_result.archive_count,
            successful_items=discovery_result.archive_count,
            failed_items=0,
            skipped_items=0,
            current_archive=current_archive,
            current_mailbox=None,
            current_item=None,
            started_at=started_at,
            last_updated=discovered_at,
        )

    def _resolve_metrics(
        self,
        *,
        metrics: MigrationMetrics | None,
        discovery_result: ArchiveDiscoveryResult,
        filtered_archives: int,
        started_at: datetime,
        discovered_at: datetime,
    ) -> MigrationMetrics:
        """Resolve the discovery metrics for the current execution state."""

        elapsed_seconds = max((discovered_at - started_at).total_seconds(), 0.0)
        processed_items = discovery_result.archive_count
        throughput = processed_items / elapsed_seconds if elapsed_seconds > 0.0 else 0.0

        if metrics is not None:
            return replace(
                metrics,
                duration_seconds=elapsed_seconds,
                throughput_items_per_second=throughput,
                total_items=discovery_result.archive_count,
                processed_items=processed_items,
                successful_items=processed_items,
                failed_items=0,
                skipped_items=0,
                filtered_archives=filtered_archives,
                filtered_items=0,
                retried_items=0,
                uploaded_items=0,
                verification_failures=0,
                started_at=started_at,
                finished_at=discovered_at,
            )

        return MigrationMetrics(
            duration_seconds=elapsed_seconds,
            throughput_items_per_second=throughput,
            average_item_size=0,
            processed_bytes=0,
            estimated_remaining_seconds=None,
            peak_memory_usage_mb=None,
            total_items=discovery_result.archive_count,
            processed_items=processed_items,
            successful_items=processed_items,
            failed_items=0,
            skipped_items=0,
            filtered_archives=filtered_archives,
            filtered_items=0,
            retried_items=0,
            uploaded_items=0,
            verification_failures=0,
            total_bytes=0,
            started_at=started_at,
            finished_at=discovered_at,
        )

    def _resolve_report(
        self,
        *,
        report: ExecutionReport | None,
        metrics: MigrationMetrics,
        configuration: MigrationConfiguration,
        started_at: datetime,
        discovered_at: datetime,
    ) -> ExecutionReport:
        """Resolve the execution report for the discovery step."""

        duration_seconds = max((discovered_at - started_at).total_seconds(), 0.0)
        if report is not None:
            return replace(
                report,
                successful_steps=1,
                failed_steps=0,
                skipped_steps=0,
                duration_seconds=duration_seconds,
                completed=True,
                metrics=metrics,
                archive_names=configuration.archive_names,
                folder_paths=configuration.folder_paths,
                start_date=configuration.start_date,
                end_date=configuration.end_date,
            )

        return ExecutionReport(
            successful_steps=1,
            failed_steps=0,
            skipped_steps=0,
            duration_seconds=duration_seconds,
            completed=True,
            metrics=metrics,
            archive_names=configuration.archive_names,
            folder_paths=configuration.folder_paths,
            start_date=configuration.start_date,
            end_date=configuration.end_date,
        )

    def _resolve_tracker(
        self,
        *,
        tracker: ProgressTracker | None,
        snapshot: ProgressSnapshot,
        metrics: MigrationMetrics,
        report: ExecutionReport,
        migration_state: MigrationState,
    ) -> ProgressTracker:
        """Return the tracker that should hold the latest discovery state."""

        if tracker is not None:
            return tracker

        return ProgressTracker(
            snapshot=snapshot,
            metrics=metrics,
            execution_report=report,
            migration_state=migration_state,
        )

    def _resolve_state(
        self,
        state_machine: MigrationStateMachine | None,
    ) -> MigrationState:
        """Resolve the discovery state without introducing business logic."""

        if state_machine is not None:
            if state_machine.can_transition(MigrationState.DISCOVERING):
                state_machine.transition_to(MigrationState.DISCOVERING)

            return state_machine.current_state

        return MigrationState.DISCOVERING


__all__: list[str] = ["DiscoverArchivesStep"]
