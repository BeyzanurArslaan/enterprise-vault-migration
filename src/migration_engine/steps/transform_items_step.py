"""Transform items pipeline step module.

This module defines the migration step responsible for transforming extracted
Enterprise Vault items into target-neutral document structures. The step keeps
the orchestration layer deterministic and does not perform any persistence or
target-specific mapping.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from mock_ev.entities import Archive, Attachment, Mailbox, MailItem, VaultStore
from mock_ev.generators import DatasetGenerator

from ..contracts import ExecutionContext, ExecutionReport, PipelineStep, ProgressSnapshot
from ..discovery import ArchiveDiscoveryResult
from ..extraction import ExtractionResult
from ..metrics import MigrationMetrics
from ..progress_tracker import ProgressTracker
from ..state_machine import MigrationState, MigrationStateMachine
from ..step_context import MigrationStepContext
from ..transformation import TransformationResult, TransformedDocument

_DEFAULT_DATASET_SEED: int = 0


class TransformItemsStep(PipelineStep):
    """Transform extracted Enterprise Vault items into target-neutral documents."""

    def __init__(
        self,
        *,
        vault_stores: Sequence[VaultStore] | None = None,
        dataset_generator: DatasetGenerator | None = None,
    ) -> None:
        """Create a transformation step with optional deterministic overrides."""

        self._vault_stores = tuple(vault_stores) if vault_stores is not None else None
        self._dataset_generator = dataset_generator or DatasetGenerator(seed=_DEFAULT_DATASET_SEED)

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare item transformation for the current migration context."""

        return None

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute item transformation for the current migration context."""

        updated_context = self.transform(self._build_step_context(context))
        if updated_context.execution_report is None:
            message = "Item transformation did not produce an execution report"
            raise RuntimeError(message)

        return updated_context.execution_report

    def finalize(self, context: ExecutionContext) -> None:
        """Finalize item transformation after execution."""

        return None

    def rollback(self, context: ExecutionContext) -> None:
        """Rollback item transformation after failure."""

        return None

    def transform(self, context: MigrationStepContext) -> MigrationStepContext:
        """Transform extracted items into target-neutral document structures."""

        if context.extraction_result is None:
            message = "Transformation requires extraction results"
            raise ValueError(message)

        source_vault_stores = self._resolve_vault_stores(context.vault_stores)
        selected_vault_stores = self._select_vault_stores(
            source_vault_stores,
            context.discovery_result.vault_store_names if context.discovery_result else (),
        )
        transformed_documents: list[TransformedDocument] = []
        current_archive_name: str | None = None
        current_mailbox_address: str | None = None
        current_item_name: str | None = None

        for mail_item, (archive, mailbox) in zip(
            context.extraction_result.extracted_mail_items,
            self._iter_mail_item_contexts(selected_vault_stores),
            strict=True,
        ):
            transformed_document = self._transform_mail_item(
                archive_name=archive.name,
                mailbox_address=mailbox.address,
                mail_item=mail_item,
            )
            transformed_documents.append(transformed_document)
            current_archive_name = archive.name
            current_mailbox_address = mailbox.address
            current_item_name = transformed_document.filename

        started_at = context.execution_context.started_at
        completed_at = context.execution_context.current_timestamp or started_at
        skipped_items = 0
        failed_items = 0
        warnings: tuple[str, ...] = ()
        transformation_result = TransformationResult(
            transformed_documents=tuple(transformed_documents),
            skipped_items=skipped_items,
            failed_items=failed_items,
            warnings=warnings,
            started_at=started_at,
            completed_at=completed_at,
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
            transformed_documents=transformation_result.transformed_documents,
            skipped_items=skipped_items,
            failed_items=failed_items,
            started_at=started_at,
            completed_at=completed_at,
        )
        updated_snapshot = self._build_snapshot(
            transformed_documents=transformation_result.transformed_documents,
            skipped_items=skipped_items,
            failed_items=failed_items,
            started_at=started_at,
            completed_at=completed_at,
            current_archive_name=current_archive_name,
            current_mailbox_address=current_mailbox_address,
            current_item_name=current_item_name,
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
            started_at=started_at,
            completed_at=completed_at,
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
            current_timestamp=completed_at,
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
            extraction_result=context.extraction_result,
            transformation_result=transformation_result,
        )

    def _build_step_context(self, context: ExecutionContext) -> MigrationStepContext:
        """Wrap a legacy execution context in a migration step context."""

        vault_stores = self._resolve_vault_stores(None)
        discovery_result = self._build_discovery_result(vault_stores)
        extraction_result = self._build_extraction_result(vault_stores)
        return MigrationStepContext(
            execution_context=context,
            progress_tracker=context.progress_tracker,
            state_machine=None,
            execution_report=None,
            discovery_result=discovery_result,
            vault_stores=vault_stores,
            extraction_result=extraction_result,
        )

    def _resolve_vault_stores(
        self,
        vault_stores: Sequence[VaultStore] | None,
    ) -> tuple[VaultStore, ...]:
        """Return the source vault stores to inspect during transformation."""

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

    def _build_extraction_result(
        self,
        vault_stores: Sequence[VaultStore],
    ) -> ExtractionResult:
        """Create a structural extraction summary for the source vault stores."""

        discovered_archives: list[Archive] = []
        extracted_mailboxes: list[Mailbox] = []
        extracted_mail_items: list[MailItem] = []
        extracted_attachments: list[Attachment] = []
        for vault_store in vault_stores:
            for archive in vault_store.archives:
                discovered_archives.append(archive)
                for mailbox in archive.mailboxes:
                    extracted_mailboxes.append(mailbox)
                    for mail_item in mailbox.mail_items:
                        extracted_mail_items.append(mail_item)
                        extracted_attachments.extend(mail_item.attachments)

        return ExtractionResult(
            discovered_archives=tuple(discovered_archives),
            extracted_mailboxes=tuple(extracted_mailboxes),
            extracted_mail_items=tuple(extracted_mail_items),
            extracted_attachments=tuple(extracted_attachments),
            total_mailboxes=len(extracted_mailboxes),
            total_items=len(extracted_mail_items),
            total_attachments=len(extracted_attachments),
        )

    def _select_vault_stores(
        self,
        vault_stores: Sequence[VaultStore],
        vault_store_names: Sequence[str],
    ) -> tuple[VaultStore, ...]:
        """Select vault stores in the order declared by discovery."""

        if not vault_store_names:
            return tuple(vault_stores)

        store_by_name = {vault_store.name: vault_store for vault_store in vault_stores}
        selected_stores = [
            store_by_name[name] for name in vault_store_names if name in store_by_name
        ]
        return tuple(selected_stores)

    def _iter_mail_item_contexts(
        self,
        vault_stores: Sequence[VaultStore],
    ) -> list[tuple[Archive, Mailbox]]:
        """Collect archive and mailbox context for each mail item."""

        mail_item_contexts: list[tuple[Archive, Mailbox]] = []
        for vault_store in vault_stores:
            for archive in vault_store.archives:
                for mailbox in archive.mailboxes:
                    mail_item_contexts.extend((archive, mailbox) for _ in mailbox.mail_items)

        return mail_item_contexts

    def _transform_mail_item(
        self,
        *,
        archive_name: str,
        mailbox_address: str,
        mail_item: MailItem,
    ) -> TransformedDocument:
        """Transform a mail item into a deterministic neutral document."""

        attachment_sizes = tuple(attachment.size_bytes for attachment in mail_item.attachments)
        attachment_filenames = tuple(attachment.filename for attachment in mail_item.attachments)
        attachment_checksums = tuple(attachment.checksum for attachment in mail_item.attachments)
        attachment_bytes = sum(attachment_sizes)
        document_size = mail_item.message_size + attachment_bytes
        metadata_properties = (
            ("internet_message_id", mail_item.internet_message_id),
            ("message_size", str(mail_item.message_size)),
            ("attachment_count", str(len(mail_item.attachments))),
        )
        return TransformedDocument(
            source_identifier=mail_item.internet_message_id,
            archive_name=archive_name,
            mailbox_address=mailbox_address,
            subject=mail_item.subject,
            filename=f"{mail_item.subject}.eml",
            content_type="message/rfc822",
            size_bytes=document_size,
            checksum=mail_item.internet_message_id,
            sender=mail_item.sender,
            recipients=tuple(mail_item.recipients),
            cc_recipients=tuple(mail_item.cc_recipients),
            bcc_recipients=tuple(mail_item.bcc_recipients),
            retention_policy=mail_item.retention_policy.name,
            department=self._derive_department(mailbox_address),
            tags=(archive_name, mailbox_address, mail_item.conversation_id),
            custom_properties=metadata_properties,
            attachment_filenames=attachment_filenames,
            attachment_checksums=attachment_checksums,
            attachment_sizes=attachment_sizes,
            created_at=mail_item.sent_at,
            modified_at=mail_item.modified_at,
        )

    def _derive_department(self, mailbox_address: str) -> str:
        """Derive a deterministic department label from the mailbox address."""

        if "@" not in mailbox_address:
            return "Unknown"

        domain = mailbox_address.split("@", maxsplit=1)[1]
        return domain.split(".", maxsplit=1)[0].title()

    def _build_snapshot(
        self,
        *,
        transformed_documents: Sequence[TransformedDocument],
        skipped_items: int,
        failed_items: int,
        started_at: datetime,
        completed_at: datetime,
        current_archive_name: str | None,
        current_mailbox_address: str | None,
        current_item_name: str | None,
    ) -> ProgressSnapshot:
        """Build the updated progress snapshot for transformation bookkeeping."""

        total_items = len(transformed_documents) + skipped_items + failed_items
        processed_items = len(transformed_documents) + skipped_items + failed_items
        successful_items = len(transformed_documents)
        return ProgressSnapshot(
            total_items=total_items,
            processed_items=processed_items,
            successful_items=successful_items,
            failed_items=failed_items,
            skipped_items=skipped_items,
            current_archive=current_archive_name,
            current_mailbox=current_mailbox_address,
            current_item=current_item_name,
            started_at=started_at,
            last_updated=completed_at,
        )

    def _resolve_metrics(
        self,
        *,
        metrics: MigrationMetrics | None,
        transformed_documents: Sequence[TransformedDocument],
        skipped_items: int,
        failed_items: int,
        started_at: datetime,
        completed_at: datetime,
    ) -> MigrationMetrics:
        """Resolve the metrics object for the current transformation state."""

        duration_seconds = max((completed_at - started_at).total_seconds(), 0.0)
        processed_items = len(transformed_documents)
        processed_bytes = sum(document.size_bytes for document in transformed_documents)
        throughput = processed_items / duration_seconds if duration_seconds > 0.0 else 0.0
        average_item_size = processed_bytes // processed_items if processed_items > 0 else 0

        if metrics is not None:
            return replace(
                metrics,
                duration_seconds=duration_seconds,
                throughput_items_per_second=throughput,
                average_item_size=average_item_size,
                processed_bytes=processed_bytes,
                total_items=processed_items + skipped_items + failed_items,
                processed_items=processed_items,
                successful_items=processed_items,
                failed_items=failed_items,
                skipped_items=skipped_items,
                retried_items=0,
                uploaded_items=0,
                verification_failures=0,
                total_bytes=processed_bytes,
                started_at=started_at,
                finished_at=completed_at,
            )

        return MigrationMetrics(
            duration_seconds=duration_seconds,
            throughput_items_per_second=throughput,
            average_item_size=average_item_size,
            processed_bytes=processed_bytes,
            estimated_remaining_seconds=None,
            peak_memory_usage_mb=None,
            total_items=processed_items + skipped_items + failed_items,
            processed_items=processed_items,
            successful_items=processed_items,
            failed_items=failed_items,
            skipped_items=skipped_items,
            retried_items=0,
            uploaded_items=0,
            verification_failures=0,
            total_bytes=processed_bytes,
            started_at=started_at,
            finished_at=completed_at,
        )

    def _resolve_report(
        self,
        *,
        report: ExecutionReport | None,
        metrics: MigrationMetrics,
        started_at: datetime,
        completed_at: datetime,
    ) -> ExecutionReport:
        """Resolve the execution report for the transformation step."""

        duration_seconds = max((completed_at - started_at).total_seconds(), 0.0)
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
        """Return the tracker that should hold the latest transformation state."""

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
        """Resolve the transformation state without introducing business logic."""

        if state_machine is not None:
            if state_machine.can_transition(MigrationState.TRANSFORMING):
                state_machine.transition_to(MigrationState.TRANSFORMING)

            return state_machine.current_state

        return MigrationState.TRANSFORMING


__all__: list[str] = ["TransformItemsStep"]
