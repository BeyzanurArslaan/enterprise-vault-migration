"""Extract items pipeline step module.

This module defines the second executable migration step responsible for
reading the discovered Enterprise Vault archives and producing a structural
extraction result. The step only aggregates existing source entities and does
not perform any transformation or upload behavior.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from mock_ev.entities import (
    Archive,
    Attachment,
    Mailbox,
    MailItem,
    VaultStore,
)
from mock_ev.generators import DatasetGenerator

from ..contracts import (
    ExecutionContext,
    ExecutionReport,
    PipelineStep,
    ProgressSnapshot,
)
from ..discovery import ArchiveDiscoveryResult
from ..extraction import ExtractionResult
from ..metrics import MigrationMetrics
from ..progress_tracker import ProgressTracker
from ..state_machine import MigrationState, MigrationStateMachine
from ..step_context import MigrationStepContext

_DEFAULT_DATASET_SEED: int = 0


class ExtractItemsStep(PipelineStep):
    """Extract mailboxes, mail items, and attachments from archives."""

    def __init__(
        self,
        *,
        vault_stores: Sequence[VaultStore] | None = None,
        dataset_generator: DatasetGenerator | None = None,
    ) -> None:
        """Create an extraction step with optional deterministic data overrides."""

        self._vault_stores = tuple(vault_stores) if vault_stores is not None else None
        self._dataset_generator = dataset_generator or DatasetGenerator(seed=_DEFAULT_DATASET_SEED)

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare item extraction for the current migration context."""

        return None

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute item extraction for the current migration context."""

        updated_context = self.extract(self._build_step_context(context))
        if updated_context.execution_report is None:
            message = "Item extraction did not produce an execution report"
            raise RuntimeError(message)

        return updated_context.execution_report

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize item extraction after execution."""

        return None

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback item extraction after failure."""

        return None

    def extract(self, context: MigrationStepContext) -> MigrationStepContext:
        """Extract runtime objects from the discovered source archives."""

        if context.discovery_result is None:
            message = "Extraction requires archive discovery results"
            raise ValueError(message)

        source_vault_stores = self._resolve_vault_stores(context.vault_stores)
        selected_vault_stores = self._select_vault_stores(
            source_vault_stores,
            context.discovery_result.vault_store_names,
        )
        discovered_archives = self._select_archives(
            selected_vault_stores,
            context.discovery_result.archive_names,
        )
        extracted_mailboxes: list[Mailbox] = []
        extracted_mail_items: list[MailItem] = []
        extracted_attachments: list[Attachment] = []
        current_archive_name: str | None = None
        current_mailbox_address: str | None = None
        current_item_subject: str | None = None

        for archive in discovered_archives:
            current_archive_name = archive.name
            for mailbox in archive.mailboxes:
                extracted_mailboxes.append(mailbox)
                current_mailbox_address = mailbox.address
                for mail_item in mailbox.mail_items:
                    extracted_mail_items.append(mail_item)
                    current_item_subject = mail_item.subject
                    extracted_attachments.extend(mail_item.attachments)

        discovered_at = (
            context.execution_context.current_timestamp or context.execution_context.started_at
        )
        extraction_result = ExtractionResult(
            discovered_archives=tuple(discovered_archives),
            extracted_mailboxes=tuple(extracted_mailboxes),
            extracted_mail_items=tuple(extracted_mail_items),
            extracted_attachments=tuple(extracted_attachments),
            total_mailboxes=len(extracted_mailboxes),
            total_items=len(extracted_mail_items),
            total_attachments=len(extracted_attachments),
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
            extraction_result=extraction_result,
            started_at=context.execution_context.started_at,
            finished_at=discovered_at,
        )
        updated_snapshot = self._build_snapshot(
            extraction_result=extraction_result,
            started_at=context.execution_context.started_at,
            finished_at=discovered_at,
            current_archive_name=current_archive_name,
            current_mailbox_address=current_mailbox_address,
            current_item_subject=current_item_subject,
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
            started_at=context.execution_context.started_at,
            finished_at=discovered_at,
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
            discovery_result=context.discovery_result,
            vault_stores=selected_vault_stores,
            extraction_result=extraction_result,
        )

    def _build_step_context(self, context: ExecutionContext) -> MigrationStepContext:
        """Wrap a legacy execution context in a migration step context."""

        vault_stores = self._resolve_vault_stores(None)
        discovery_result = self._build_discovery_result(vault_stores)
        return MigrationStepContext(
            execution_context=context,
            progress_tracker=context.progress_tracker,
            state_machine=None,
            execution_report=None,
            discovery_result=discovery_result,
            vault_stores=vault_stores,
        )

    def _resolve_vault_stores(
        self,
        vault_stores: Sequence[VaultStore] | None,
    ) -> tuple[VaultStore, ...]:
        """Return the source vault stores to inspect during extraction."""

        if vault_stores is not None:
            return tuple(vault_stores)
        if self._vault_stores is not None:
            return self._vault_stores

        return tuple(self._dataset_generator.generate_small())

    def _build_discovery_result(
        self,
        vault_stores: Sequence[VaultStore],
    ) -> ArchiveDiscoveryResult:
        """Create a structural summary of the source vault stores."""

        vault_store_names = tuple(store.name for store in vault_stores)
        archive_names = tuple(archive.name for store in vault_stores for archive in store.archives)
        return ArchiveDiscoveryResult(
            vault_store_names=vault_store_names,
            archive_names=archive_names,
            vault_store_count=len(vault_store_names),
            archive_count=len(archive_names),
        )

    def _select_vault_stores(
        self,
        vault_stores: Sequence[VaultStore],
        vault_store_names: Sequence[str],
    ) -> tuple[VaultStore, ...]:
        """Select vault stores in the order declared by the discovery result."""

        if not vault_store_names:
            return tuple(vault_stores)

        store_by_name = {vault_store.name: vault_store for vault_store in vault_stores}
        selected_stores = [
            store_by_name[name] for name in vault_store_names if name in store_by_name
        ]
        return tuple(selected_stores)

    def _select_archives(
        self,
        vault_stores: Sequence[VaultStore],
        archive_names: Sequence[str],
    ) -> tuple[Archive, ...]:
        """Select archives from the discovered vault stores."""

        if not archive_names:
            return tuple(archive for store in vault_stores for archive in store.archives)

        selected_archives: list[Archive] = []
        for vault_store in vault_stores:
            for archive in vault_store.archives:
                if archive.name in archive_names:
                    selected_archives.append(archive)

        return tuple(selected_archives)

    def _build_snapshot(
        self,
        *,
        extraction_result: ExtractionResult,
        started_at: datetime,
        finished_at: datetime,
        current_archive_name: str | None,
        current_mailbox_address: str | None,
        current_item_subject: str | None,
    ) -> ProgressSnapshot:
        """Build the updated progress snapshot for extraction bookkeeping."""

        return ProgressSnapshot(
            total_items=extraction_result.total_items,
            processed_items=extraction_result.total_items,
            successful_items=extraction_result.total_items,
            failed_items=0,
            skipped_items=0,
            current_archive=current_archive_name,
            current_mailbox=current_mailbox_address,
            current_item=current_item_subject,
            started_at=started_at,
            last_updated=finished_at,
        )

    def _resolve_metrics(
        self,
        *,
        metrics: MigrationMetrics | None,
        extraction_result: ExtractionResult,
        started_at: datetime,
        finished_at: datetime,
    ) -> MigrationMetrics:
        """Resolve the metrics object for the current extraction state."""

        duration_seconds = max((finished_at - started_at).total_seconds(), 0.0)
        processed_items = extraction_result.total_items
        processed_bytes = sum(
            mail_item.message_size for mail_item in extraction_result.extracted_mail_items
        )
        processed_bytes += sum(
            attachment.size_bytes for attachment in extraction_result.extracted_attachments
        )
        throughput = processed_items / duration_seconds if duration_seconds > 0.0 else 0.0
        average_item_size = processed_bytes // processed_items if processed_items > 0 else 0

        if metrics is not None:
            return replace(
                metrics,
                duration_seconds=duration_seconds,
                throughput_items_per_second=throughput,
                average_item_size=average_item_size,
                processed_bytes=processed_bytes,
                total_items=processed_items,
                processed_items=processed_items,
                successful_items=processed_items,
                failed_items=0,
                skipped_items=0,
                retried_items=0,
                uploaded_items=0,
                verification_failures=0,
                total_bytes=processed_bytes,
                started_at=started_at,
                finished_at=finished_at,
            )

        return MigrationMetrics(
            duration_seconds=duration_seconds,
            throughput_items_per_second=throughput,
            average_item_size=average_item_size,
            processed_bytes=processed_bytes,
            estimated_remaining_seconds=None,
            peak_memory_usage_mb=None,
            total_items=processed_items,
            processed_items=processed_items,
            successful_items=processed_items,
            failed_items=0,
            skipped_items=0,
            retried_items=0,
            uploaded_items=0,
            verification_failures=0,
            total_bytes=processed_bytes,
            started_at=started_at,
            finished_at=finished_at,
        )

    def _resolve_report(
        self,
        *,
        report: ExecutionReport | None,
        metrics: MigrationMetrics,
        started_at: datetime,
        finished_at: datetime,
    ) -> ExecutionReport:
        """Resolve the execution report for the current extraction state."""

        duration_seconds = max((finished_at - started_at).total_seconds(), 0.0)
        if report is not None:
            return replace(
                report,
                successful_steps=1,
                failed_steps=0,
                skipped_steps=0,
                duration_seconds=duration_seconds,
                completed=True,
                metrics=metrics,
            )

        return ExecutionReport(
            successful_steps=1,
            failed_steps=0,
            skipped_steps=0,
            duration_seconds=duration_seconds,
            completed=True,
            metrics=metrics,
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
        """Return the tracker that should hold the latest extraction state."""

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
        """Resolve the extraction state without introducing business logic."""

        if state_machine is not None:
            if state_machine.can_transition(MigrationState.EXTRACTING):
                state_machine.transition_to(MigrationState.EXTRACTING)

            return state_machine.current_state

        return MigrationState.EXTRACTING


__all__: list[str] = ["ExtractItemsStep"]
