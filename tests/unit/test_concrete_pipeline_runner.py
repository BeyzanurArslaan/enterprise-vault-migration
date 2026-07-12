"""Integration-style regression tests for the concrete migration pipeline.

This module validates the real discovery, extraction, transformation, upload,
verification, and finalization flow driven by the concrete runner and step
registry. The tests stay within the orchestration layer and keep the target
adapter boundary explicit.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest

from adapters.target import MockStorionXTargetAdapter
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import (
    ExecutionContext,
    ExecutionReport,
    PipelineStep,
    ProgressSnapshot,
)
from migration_engine.execution_result import ExecutionResult
from migration_engine.metrics import MigrationMetrics
from migration_engine.pipeline import MigrationPipeline
from migration_engine.progress_tracker import ProgressTracker
from migration_engine.runner import PipelineRunner, StepRegistry
from migration_engine.state_machine import MigrationState, MigrationStateMachine
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import (
    DiscoverArchivesStep,
    ExtractItemsStep,
    FinalizeMigrationStep,
    TransformItemsStep,
    UploadItemsStep,
    VerifyItemsStep,
)
from migration_engine.transformation import TransformedDocument
from mock_ev.entities import Archive, Attachment, Mailbox, MailItem, RetentionPolicy, VaultStore
from mock_storionx.entities import Document


def _build_retention_policy() -> RetentionPolicy:
    """Create a deterministic retention policy for concrete workflow tests."""

    return RetentionPolicy(
        name="Standard",
        retention_days=30,
        classification="general",
    )


def _build_attachment(filename: str, size_bytes: int) -> Attachment:
    """Create a deterministic attachment for concrete workflow tests."""

    return Attachment(
        filename=filename,
        extension="txt",
        mime_type="text/plain",
        size_bytes=size_bytes,
        checksum=f"checksum-{filename}",
    )


def _build_mail_item(
    *,
    subject: str,
    message_size: int,
    attachment_sizes: tuple[int, ...],
) -> MailItem:
    """Create a deterministic mail item for concrete workflow tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    attachments = [
        _build_attachment(filename=f"{subject}-{index}.txt", size_bytes=size_bytes)
        for index, size_bytes in enumerate(attachment_sizes, start=1)
    ]
    return MailItem(
        subject=subject,
        sender="sender@example.com",
        body="Body",
        received_at=timestamp,
        sent_at=timestamp,
        modified_at=timestamp,
        internet_message_id=f"message-{subject}",
        conversation_id=f"conversation-{subject}",
        message_size=message_size,
        retention_policy=_build_retention_policy(),
        recipients=["recipient@example.com"],
        cc_recipients=["cc@example.com"],
        bcc_recipients=[],
        attachments=attachments,
    )


def _build_mailbox(address: str, mail_items: tuple[MailItem, ...]) -> Mailbox:
    """Create a deterministic mailbox for concrete workflow tests."""

    return Mailbox(address=address, mail_items=list(mail_items))


def _build_archive(name: str, mailboxes: tuple[Mailbox, ...]) -> Archive:
    """Create a deterministic archive for concrete workflow tests."""

    return Archive(name=name, mailboxes=list(mailboxes))


def _build_vault_store(name: str, archives: tuple[Archive, ...]) -> VaultStore:
    """Create a deterministic vault store for concrete workflow tests."""

    return VaultStore(name=name, archives=list(archives))


def _build_vault_stores() -> tuple[VaultStore, ...]:
    """Create a small deterministic Enterprise Vault dataset."""

    archive = _build_archive(
        "Archive One",
        (
            _build_mailbox(
                "alice@example.com",
                (
                    _build_mail_item(
                        subject="Quarterly-Report",
                        message_size=2048,
                        attachment_sizes=(512,),
                    ),
                    _build_mail_item(
                        subject="Annual-Report",
                        message_size=1024,
                        attachment_sizes=(),
                    ),
                ),
            ),
        ),
    )
    return (_build_vault_store("Vault Store One", (archive,)),)


def _build_progress_tracker(started_at: datetime) -> ProgressTracker:
    """Create a deterministic progress tracker for concrete workflow tests."""

    return ProgressTracker(
        snapshot=ProgressSnapshot(
            total_items=0,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            current_archive=None,
            current_mailbox=None,
            current_item=None,
            started_at=started_at,
            last_updated=started_at,
        ),
        migration_state=MigrationState.CREATED,
    )


def _build_initial_context(started_at: datetime) -> MigrationStepContext:
    """Create an initial migration step context for runner integration tests."""

    progress_tracker = _build_progress_tracker(started_at)
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(),
        started_at=started_at,
        current_step=None,
        metrics=MigrationMetrics(
            duration_seconds=0.0,
            throughput_items_per_second=0.0,
            average_item_size=0,
            processed_bytes=0,
            estimated_remaining_seconds=None,
            peak_memory_usage_mb=None,
            total_items=0,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            retried_items=0,
            uploaded_items=0,
            verification_failures=0,
            total_bytes=0,
            started_at=started_at,
            finished_at=started_at,
        ),
        progress_tracker=progress_tracker,
        state=MigrationState.CREATED,
        current_timestamp=started_at,
    )
    return MigrationStepContext(
        execution_context=execution_context,
        progress_tracker=progress_tracker,
        state_machine=MigrationStateMachine(current_state=MigrationState.CREATED),
    )


def _build_concrete_steps(
    *,
    vault_stores: tuple[VaultStore, ...],
    target_port: MockStorionXTargetAdapter,
) -> tuple[
    DiscoverArchivesStep,
    ExtractItemsStep,
    TransformItemsStep,
    UploadItemsStep,
    VerifyItemsStep,
    FinalizeMigrationStep,
]:
    """Create the concrete migration steps for the full workflow."""

    return (
        DiscoverArchivesStep(vault_stores=vault_stores),
        ExtractItemsStep(),
        TransformItemsStep(vault_stores=vault_stores),
        UploadItemsStep(target_port=target_port),
        VerifyItemsStep(target_port=target_port),
        FinalizeMigrationStep(),
    )


def _build_runner(
    *,
    vault_stores: tuple[VaultStore, ...],
    target_port: MockStorionXTargetAdapter,
    started_at: datetime,
) -> PipelineRunner:
    """Create a runner configured with the concrete migration workflow."""

    discover_step, extract_step, transform_step, upload_step, verify_step, finalize_step = (
        _build_concrete_steps(vault_stores=vault_stores, target_port=target_port)
    )
    pipeline = MigrationPipeline(
        steps=(
            finalize_step,
            verify_step,
            upload_step,
            transform_step,
            extract_step,
            discover_step,
        ),
    )
    return PipelineRunner(
        pipeline.steps,
        pipeline=pipeline,
        initial_context=_build_initial_context(started_at),
    )


def test_step_registry_resolves_concrete_steps_in_required_order() -> None:
    """The registry should resolve concrete steps in canonical pipeline order."""

    target_port = MockStorionXTargetAdapter()
    registry = StepRegistry(
        (
            VerifyItemsStep(target_port=target_port),
            DiscoverArchivesStep(),
            FinalizeMigrationStep(),
            UploadItemsStep(target_port=target_port),
            TransformItemsStep(),
            ExtractItemsStep(),
        ),
    )

    assert [step.__class__.__name__ for step in registry.resolve()] == [
        "DiscoverArchivesStep",
        "ExtractItemsStep",
        "TransformItemsStep",
        "UploadItemsStep",
        "VerifyItemsStep",
        "FinalizeMigrationStep",
    ]


def test_step_registry_rejects_duplicate_registration() -> None:
    """The registry should reject duplicate concrete step types."""

    with pytest.raises(ValueError, match="Duplicate step registration is not allowed"):
        StepRegistry((DiscoverArchivesStep(), DiscoverArchivesStep()))


def test_pipeline_runner_executes_full_concrete_workflow_successfully() -> None:
    """The runner should complete the real concrete workflow end to end."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    vault_stores = _build_vault_stores()
    target_port = MockStorionXTargetAdapter(started_at=started_at)
    runner = _build_runner(
        vault_stores=vault_stores,
        target_port=target_port,
        started_at=started_at,
    )

    result = runner.run()

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.errors == ()
    assert result.warnings == ()
    assert result.execution_report is not None
    assert result.execution_report.completed is True
    assert result.execution_report.metrics is not None
    assert result.execution_report.metrics.total_items == 2
    assert result.execution_report.metrics.processed_items == 2
    assert result.execution_report.metrics.successful_items == 2
    assert result.execution_report.metrics.failed_items == 0
    assert result.execution_report.metrics.uploaded_items == 2
    assert result.execution_report.metrics.verification_failures == 0
    assert result.completed_at is not None
    assert result.duration is not None
    assert result.duration.total_seconds() >= 0.0
    assert runner.execution_result == result
    assert runner.execution_context is not None
    assert runner.execution_context.state == MigrationState.COMPLETED
    assert runner.execution_context.current_step == "FinalizeMigrationStep"
    assert runner.progress_tracker is not None
    assert runner.progress_tracker.current_migration_state == MigrationState.COMPLETED
    assert runner.progress_tracker.current_snapshot.total_items == 2
    assert runner.progress_tracker.current_snapshot.successful_items == 2
    assert runner.progress_tracker.current_snapshot.failed_items == 0
    assert runner.current_step_context is not None
    assert runner.current_step_context.discovery_result is not None
    assert runner.current_step_context.extraction_result is not None
    assert runner.current_step_context.transformation_result is not None
    assert runner.current_step_context.upload_result is not None
    assert runner.current_step_context.verification_result is not None
    assert runner.current_step_context.execution_report is not None
    assert runner.current_step_context.execution_result is not None
    assert runner.current_step_context.execution_context.state == MigrationState.COMPLETED
    assert runner.current_step_context.upload_result.uploaded_document_ids == (
        "message-Quarterly-Report",
        "message-Annual-Report",
    )
    assert runner.current_step_context.verification_result.verified_document_ids == (
        "message-Quarterly-Report",
        "message-Annual-Report",
    )
    assert len(target_port.document_storage.list()) == 2


def test_pipeline_runner_preserves_partial_upload_failure_and_finalizes() -> None:
    """The runner should finish when upload records item-level failures."""

    class _FailingUploadAdapter(MockStorionXTargetAdapter):
        """Fail one deterministic upload while keeping successful uploads."""

        def upload_archived_file(self, archived_file_id: str, payload: object) -> Document:
            """Raise for one predetermined source identifier."""

            if archived_file_id == "message-Annual-Report":
                message = "upload failed for message-Annual-Report"
                raise RuntimeError(message)

            return super().upload_archived_file(archived_file_id, payload)

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    vault_stores = _build_vault_stores()
    target_port = _FailingUploadAdapter(started_at=started_at)
    runner = _build_runner(
        vault_stores=vault_stores,
        target_port=target_port,
        started_at=started_at,
    )

    result = runner.run()

    assert result.success is True
    assert result.errors == ()
    assert result.warnings == ("1 items failed upload",)
    assert result.execution_report is not None
    assert result.execution_report.completed is True
    assert result.execution_report.metrics is not None
    assert result.execution_report.metrics.total_items == 2
    assert result.execution_report.metrics.successful_items == 1
    assert result.execution_report.metrics.failed_items == 1
    assert result.execution_report.metrics.uploaded_items == 1
    assert result.execution_report.metrics.verification_failures == 0
    assert runner.current_step_context is not None
    assert runner.current_step_context.upload_result is not None
    assert runner.current_step_context.upload_result.uploaded_document_ids == (
        "message-Quarterly-Report",
    )
    assert runner.current_step_context.upload_result.failed_documents[0].source_identifier == (
        "message-Annual-Report"
    )
    assert runner.current_step_context.verification_result is not None
    assert runner.current_step_context.verification_result.verified_document_ids == (
        "message-Quarterly-Report",
    )
    assert runner.current_step_context.verification_result.failed_count == 0
    assert target_port.document_storage.list()[0].id == "message-Quarterly-Report"


def test_pipeline_runner_preserves_partial_verification_failure_and_finalizes() -> None:
    """The runner should finish when verification records item-level failures."""

    class _MissingDocumentAdapter(MockStorionXTargetAdapter):
        """Hide one uploaded document during verification lookups."""

        def get_uploaded_document(self, document_id: str) -> TransformedDocument | None:
            """Return no document for one predetermined source identifier."""

            if document_id == "message-Annual-Report":
                return None

            return super().get_uploaded_document(document_id)

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    vault_stores = _build_vault_stores()
    target_port = _MissingDocumentAdapter(started_at=started_at)
    runner = _build_runner(
        vault_stores=vault_stores,
        target_port=target_port,
        started_at=started_at,
    )

    result = runner.run()

    assert result.success is True
    assert result.errors == ()
    assert result.warnings == ("1 items failed verification",)
    assert result.execution_report is not None
    assert result.execution_report.completed is True
    assert result.execution_report.metrics is not None
    assert result.execution_report.metrics.total_items == 2
    assert result.execution_report.metrics.successful_items == 1
    assert result.execution_report.metrics.failed_items == 1
    assert result.execution_report.metrics.uploaded_items == 2
    assert result.execution_report.metrics.verification_failures == 1
    assert runner.current_step_context is not None
    assert runner.current_step_context.verification_result is not None
    assert runner.current_step_context.verification_result.verified_document_ids == (
        "message-Quarterly-Report",
    )
    assert runner.current_step_context.verification_result.failed_document_ids == (
        "message-Annual-Report",
    )
    assert runner.current_step_context.verification_result.missing_document_ids == (
        "message-Annual-Report",
    )


def test_pipeline_runner_rolls_back_on_unexpected_concrete_step_error() -> None:
    """The runner should roll back and fail when a concrete step raises."""

    class UploadItemsStep(PipelineStep):
        """Raise from the legacy execute path to exercise rollback behavior."""

        def prepare(self, context: ExecutionContext) -> None:
            """Prepare the failing upload step."""

            return None

        def execute(self, context: ExecutionContext) -> ExecutionReport:
            """Raise a deterministic runtime error during upload execution."""

            message = "boom"
            raise RuntimeError(message)

        def finalize(self, context: ExecutionContext) -> None:
            """Finalize the failing upload step."""

            return None

        def rollback(self, context: ExecutionContext) -> None:
            """Rollback the failing upload step."""

            return None

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    vault_stores = _build_vault_stores()
    target_port = MockStorionXTargetAdapter(started_at=started_at)
    discover_step, extract_step, transform_step, _upload_step, verify_step, finalize_step = (
        _build_concrete_steps(vault_stores=vault_stores, target_port=target_port)
    )
    runner = PipelineRunner(
        (
            discover_step,
            extract_step,
            UploadItemsStep(),
            verify_step,
            finalize_step,
        ),
        initial_context=_build_initial_context(started_at),
    )

    result = runner.run()

    assert result.success is False
    assert result.errors == ("boom",)
    assert result.execution_report is not None
    assert result.execution_report.completed is False
    assert runner.state_machine.current_state == MigrationState.FAILED
    assert runner.execution_context is not None
    assert runner.execution_context.state == MigrationState.FAILED
    assert runner.current_step_context is not None
    assert runner.current_step_context.execution_context.state == MigrationState.FAILED


def test_pipeline_runner_has_no_direct_mock_storionx_imports() -> None:
    """The migration engine should stay decoupled from mock storionX imports."""

    for path in Path("src/migration_engine").rglob("*.py"):
        source = path.read_text()
        syntax_tree = ast.parse(source)
        for node in ast.walk(syntax_tree):
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith("mock_storionx") for alias in node.names), path
            elif isinstance(node, ast.ImportFrom):
                assert not (
                    node.module is not None and node.module.startswith("mock_storionx")
                ), path


def test_pipeline_runner_uses_step_registry_and_pipeline_injection() -> None:
    """The runner should honor constructor-injected pipeline composition."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    vault_stores = _build_vault_stores()
    target_port = MockStorionXTargetAdapter(started_at=started_at)
    pipeline = MigrationPipeline(
        steps=(
            DiscoverArchivesStep(vault_stores=vault_stores),
            ExtractItemsStep(),
            TransformItemsStep(vault_stores=vault_stores),
            UploadItemsStep(target_port=target_port),
            VerifyItemsStep(target_port=target_port),
            FinalizeMigrationStep(),
        ),
    )
    step_registry = StepRegistry(pipeline.steps)
    initial_context = _build_initial_context(started_at)
    runner = PipelineRunner(
        pipeline.steps,
        pipeline=pipeline,
        step_registry=step_registry,
        initial_context=initial_context,
    )

    assert runner.step_registry is step_registry
    assert runner.pipeline is pipeline
    assert runner.initial_context is initial_context
    assert runner.steps == step_registry.resolve()
