"""End-to-end tests for the mixed mock Enterprise Vault dataset."""

from __future__ import annotations

from datetime import UTC, datetime

from adapters.target import MockStorionXTargetAdapter
from migration_engine.configuration import MigrationConfiguration
from migration_engine.contracts import ExecutionContext
from migration_engine.pipeline import MigrationPipeline
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState
from migration_engine.step_context import MigrationStepContext
from migration_engine.steps import (
    DiscoverArchivesStep,
    ExtractItemsStep,
    FinalizeMigrationStep,
    TransformItemsStep,
    UploadItemsStep,
    VerifyItemsStep,
)
from mock_ev.entities import VaultStore
from mock_ev.generators import DatasetGenerator
from mock_storionx.services import UploadService
from mock_storionx.storage import DocumentStorage


def _build_initial_context(*, dry_run: bool) -> MigrationStepContext:
    """Build an initial execution context for mixed-dataset pipeline tests."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    execution_context = ExecutionContext(
        migration_id="migration-1",
        configuration=MigrationConfiguration(dry_run=dry_run),
        started_at=started_at,
        current_step=None,
        metrics=None,
        progress_tracker=None,
        state=MigrationState.CREATED,
        current_timestamp=started_at,
    )
    return MigrationStepContext(execution_context=execution_context)


def _build_pipeline(
    *,
    vault_stores: tuple[VaultStore, ...],
    target_port: MockStorionXTargetAdapter,
) -> MigrationPipeline:
    """Build the canonical pipeline used by the mixed-dataset end-to-end tests."""

    return MigrationPipeline(
        steps=(
            DiscoverArchivesStep(vault_stores=vault_stores),
            ExtractItemsStep(vault_stores=vault_stores),
            TransformItemsStep(vault_stores=vault_stores),
            UploadItemsStep(target_port=target_port),
            VerifyItemsStep(target_port=target_port),
            FinalizeMigrationStep(),
        ),
    )


def _build_target_adapter(*, started_at: datetime) -> MockStorionXTargetAdapter:
    """Build the concrete mock storionX target adapter for end-to-end tests."""

    return MockStorionXTargetAdapter(
        started_at=started_at,
        session_id="session-1",
        upload_service=UploadService(),
        document_storage=DocumentStorage(),
    )


def test_mixed_dataset_dry_run_keeps_target_storage_empty() -> None:
    """Dry-run execution should process the mixed dataset without target mutation."""

    vault_stores = tuple(DatasetGenerator(seed=31).generate_mixed())
    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    target_port = _build_target_adapter(started_at=started_at)
    runner = PipelineRunner(
        pipeline=_build_pipeline(vault_stores=vault_stores, target_port=target_port),
        initial_context=_build_initial_context(dry_run=True),
    )

    result = runner.run()

    assert result.success is True
    assert target_port.document_storage.list() == []
    assert runner.current_step_context is not None
    assert runner.current_step_context.extraction_result is not None
    assert runner.current_step_context.extraction_result.unsupported_archives
    assert (
        runner.current_step_context.extraction_result.unsupported_archives[0].name == "FSA Archive"
    )


def test_mixed_dataset_full_pipeline_preserves_supported_metadata() -> None:
    """The full pipeline should migrate supported mixed-dataset items end to end."""

    vault_stores = tuple(DatasetGenerator(seed=37).generate_mixed())
    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    target_port = _build_target_adapter(started_at=started_at)
    runner = PipelineRunner(
        pipeline=_build_pipeline(vault_stores=vault_stores, target_port=target_port),
        initial_context=_build_initial_context(dry_run=False),
    )

    result = runner.run()

    assert result.success is True
    assert len(target_port.document_storage.list()) == 5
    journal_document = target_port.get_uploaded_document("journal-item-1")
    assert journal_document is not None
    assert journal_document.archive_type.value == "journal"
    assert journal_document.item_type.value == "journal"
    assert journal_document.mailbox_address is None
    assert journal_document.legal_hold is True
    orphan_document = target_port.get_uploaded_document("orphaned-item-1")
    assert orphan_document is not None
    assert orphan_document.is_orphaned is True
    assert orphan_document.original_owner_identifier == "orphaned.owner@example.com"
    assert runner.current_step_context is not None
    assert runner.current_step_context.execution_report is not None
    assert any(
        "Unsupported archive type" in warning
        for warning in runner.current_step_context.execution_report.warnings
    )
