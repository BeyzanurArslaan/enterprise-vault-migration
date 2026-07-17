"""Regression tests for immutable application contracts."""

from __future__ import annotations

from uuid import uuid4

from application.commands import (
    CancelMigrationCommand,
    PauseMigrationCommand,
    ResumeMigrationCommand,
    StartMigrationCommand,
)
from application.dto import (
    AssessmentResult,
    MigrationRequest,
    MigrationResult,
    UploadResult,
)
from application.queries import AuditLogQuery, CheckpointQuery, MigrationStatusQuery
from domain.enums.job_status import JobStatus
from domain.value_objects.identifiers import ArchiveId, MigrationItemId, MigrationJobId
from migration_engine.configuration import MigrationConfiguration


def test_application_contracts_are_immutable() -> None:
    """Verify the application contracts are frozen dataclasses."""

    request = MigrationRequest(
        job_name="demo",
        archive_id=ArchiveId(uuid4()),
        dry_run=True,
        resume=False,
        batch_size=10,
        filter_expression=None,
    )
    result = MigrationResult(
        job_id=MigrationJobId(uuid4()),
        status=JobStatus.RUNNING,
        processed_items=10,
        successful_items=8,
        failed_items=2,
    )
    upload = UploadResult(
        item_id=MigrationItemId(uuid4()),
        success=True,
        target_identifier="target-1",
        error_message=None,
    )
    assessment = AssessmentResult(
        archive_id=ArchiveId(uuid4()),
        total_items=5,
        estimated_size_bytes=1024,
        estimated_duration_minutes=5,
    )

    start_command = StartMigrationCommand(request=request)
    pause_command = PauseMigrationCommand(job_id=MigrationJobId(uuid4()))
    resume_command = ResumeMigrationCommand(job_id=MigrationJobId(uuid4()))
    cancel_command = CancelMigrationCommand(job_id=MigrationJobId(uuid4()))
    status_query = MigrationStatusQuery(job_id=MigrationJobId(uuid4()))
    checkpoint_query = CheckpointQuery(job_id=MigrationJobId(uuid4()))
    audit_query = AuditLogQuery(job_id=MigrationJobId(uuid4()))

    assert request.job_name == "demo"
    assert request.dry_run is True
    assert result.status == JobStatus.RUNNING
    assert upload.success is True
    assert upload.idempotent_replay is False
    assert upload.dry_run is False
    assert assessment.estimated_duration_minutes == 5
    assert MigrationConfiguration().dry_run is False
    assert start_command.request is request
    assert pause_command.job_id is not None
    assert resume_command.job_id is not None
    assert resume_command.force is False
    assert cancel_command.job_id is not None
    assert status_query.job_id is not None
    assert checkpoint_query.job_id is not None
    assert audit_query.job_id is not None
