"""Regression tests for idempotent upload execution.

This module verifies that the upload step treats repeated source identities as
stable idempotency keys, counts replayed uploads separately from newly created
target documents, and preserves deterministic item ordering.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from application.dto import UploadResult
from domain.exceptions import IdempotencyConflictError
from domain.value_objects.identifiers import MigrationItemId
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext, ExecutionReport, ProgressSnapshot
from migration_engine.metrics import MigrationMetrics
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import UploadItemsStep
from migration_engine.transformation import TransformationResult, TransformedDocument
from ports import StorionXTargetPort


def _build_document(*, source_identifier: str, checksum: str | None = None) -> TransformedDocument:
    """Create a deterministic transformed document for upload idempotency tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    resolved_checksum = checksum or source_identifier
    return TransformedDocument(
        source_identifier=source_identifier,
        archive_name="Archive One",
        mailbox_address="alice@example.com",
        subject=f"Subject {source_identifier}",
        filename=f"{source_identifier}.eml",
        content_type="message/rfc822",
        size_bytes=256,
        checksum=resolved_checksum,
        sender="sender@example.com",
        recipients=("recipient@example.com",),
        cc_recipients=(),
        bcc_recipients=(),
        retention_policy="Standard",
        department="Finance",
        tags=("Archive One", "alice@example.com"),
        custom_properties=(("internet_message_id", source_identifier),),
        attachment_filenames=(),
        attachment_checksums=(),
        attachment_sizes=(),
        created_at=timestamp,
        modified_at=timestamp,
    )


class _IdempotentTargetPort(StorionXTargetPort):
    """Store transformed documents in memory with deterministic replay behavior."""

    def __init__(self) -> None:
        """Create an empty in-memory target port."""

        self.documents: dict[str, TransformedDocument] = {}

    def create_archive(self, archive_id: str) -> str:
        """Create an archive placeholder."""

        return archive_id

    def upload_mail_item(self, mail_item_id: str, payload: object) -> object:
        """Upload a mail item through the archived-file boundary."""

        return self.upload_archived_file(mail_item_id, payload)

    def upload_attachment(self, attachment_id: str, payload: object) -> object:
        """Upload an attachment through the archived-file boundary."""

        return self.upload_archived_file(attachment_id, payload)

    def upload_archived_file(self, archived_file_id: str, payload: object) -> UploadResult:
        """Store a document once and return replay metadata for duplicates."""

        if not isinstance(payload, TransformedDocument):
            message = "Unexpected payload"
            raise TypeError(message)

        existing_document = self.documents.get(archived_file_id)
        if existing_document is not None:
            if existing_document != payload:
                message = (
                    "Idempotency conflict for key "
                    f"{archived_file_id!r}: existing checksum "
                    f"{existing_document.checksum!r} does not match "
                    f"received checksum {payload.checksum!r}."
                )
                raise IdempotencyConflictError(message)

            return UploadResult(
                item_id=MigrationItemId(uuid5(NAMESPACE_URL, payload.source_identifier)),
                success=True,
                target_identifier=archived_file_id,
                error_message=None,
                idempotent_replay=True,
            )

        self.documents[archived_file_id] = payload
        return UploadResult(
            item_id=MigrationItemId(uuid5(NAMESPACE_URL, payload.source_identifier)),
            success=True,
            target_identifier=archived_file_id,
            error_message=None,
            idempotent_replay=False,
        )

    def finalize_job(self, job_id: str) -> str:
        """Finalize the job without changing stored documents."""

        return job_id

    def get_uploaded_document(self, document_id: str) -> TransformedDocument | None:
        """Return the stored transformed document when present."""

        return self.documents.get(document_id)


def _build_metrics() -> MigrationMetrics:
    """Create deterministic metrics for upload idempotency tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=4.0,
        throughput_items_per_second=1.0,
        average_item_size=256,
        processed_bytes=256,
        estimated_remaining_seconds=None,
        peak_memory_usage_mb=None,
        total_items=0,
        processed_items=0,
        successful_items=0,
        failed_items=0,
        skipped_items=0,
        retried_items=0,
        idempotent_replays=0,
        uploaded_items=0,
        verification_failures=0,
        total_bytes=256,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_snapshot() -> ProgressSnapshot:
    """Create a deterministic progress snapshot for upload idempotency tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return ProgressSnapshot(
        total_items=0,
        processed_items=0,
        successful_items=0,
        failed_items=0,
        skipped_items=0,
        current_archive=None,
        current_mailbox=None,
        current_item=None,
        started_at=timestamp,
        last_updated=timestamp,
    )


def _build_context(*, documents: tuple[TransformedDocument, ...]) -> MigrationStepContext:
    """Build a step context for a deterministic upload run."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at + timedelta(seconds=1)
    metrics = _build_metrics()
    progress_tracker = ProgressTracker(snapshot=_build_snapshot(), metrics=metrics)
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step="UploadItemsStep",
        metrics=metrics,
        progress_tracker=progress_tracker,
        state=MigrationState.TRANSFORMING,
        current_timestamp=completed_at,
    )
    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=progress_tracker,
        state_machine=MigrationStateMachine(current_state=MigrationState.TRANSFORMING),
        execution_report=ExecutionReport(
            successful_steps=0,
            failed_steps=0,
            skipped_steps=0,
            duration_seconds=0.0,
            completed=False,
            metrics=metrics,
        ),
        transformation_result=TransformationResult(
            transformed_documents=documents,
            skipped_items=0,
            failed_items=0,
            warnings=(),
            started_at=started_at,
            completed_at=completed_at,
        ),
    )


def test_upload_items_step_counts_replays_without_double_counting_uploaded_items() -> None:
    """Repeated uploads should count replays separately from new documents."""

    target_port = _IdempotentTargetPort()
    step = UploadItemsStep(target_port=target_port)
    first_document = _build_document(source_identifier="message-1")
    second_document = _build_document(source_identifier="message-2")

    first_context = _build_context(documents=(first_document,))
    first_result = step.upload(first_context)

    assert first_result.upload_result is not None
    assert first_result.upload_result.uploaded_document_ids == ("message-1",)
    assert first_result.upload_result.item_results[0].idempotent_replay is False
    assert first_result.execution_context.metrics is not None
    assert first_result.execution_context.metrics.uploaded_items == 1
    assert first_result.execution_context.metrics.idempotent_replays == 0

    second_context = _build_context(
        documents=(
            first_document,
            second_document,
        ),
    )
    second_result = step.upload(second_context)

    assert second_result.upload_result is not None
    assert second_result.upload_result.uploaded_document_ids == (
        "message-1",
        "message-2",
    )
    assert second_result.upload_result.item_results[0].idempotent_replay is True
    assert second_result.upload_result.item_results[1].idempotent_replay is False
    assert second_result.execution_context.metrics is not None
    assert second_result.execution_context.metrics.successful_items == 2
    assert second_result.execution_context.metrics.uploaded_items == 1
    assert second_result.execution_context.metrics.idempotent_replays == 1
    assert len(target_port.documents) == 2
