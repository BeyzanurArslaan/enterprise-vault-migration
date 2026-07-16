"""Regression tests for the in-memory retry repository adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from adapters.database import InMemoryRetryRepository
from domain.entities import RetryRecord
from domain.enums.retry_strategy import RetryStrategy
from domain.value_objects.identifiers import RetryRecordId
from ports import RetryRepositoryPort


def _build_retry_record(
    *,
    migration_job_id: str,
    step_name: str,
    attempt_number: int,
) -> RetryRecord:
    """Create a deterministic retry record for repository tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return RetryRecord(
        id=RetryRecordId(value=UUID(int=attempt_number)),
        migration_item_id=None,
        retry_strategy=RetryStrategy.FIXED_DELAY,
        attempt_number=attempt_number,
        migration_job_id=migration_job_id,
        pipeline_step_name=step_name,
        retry_reason="transient",
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_in_memory_retry_repository_satisfies_repository_port() -> None:
    """The concrete repository should implement the retry repository port."""

    repository = InMemoryRetryRepository()

    assert isinstance(repository, RetryRepositoryPort)


def test_in_memory_retry_repository_saves_and_lists_records_in_order() -> None:
    """The repository should preserve retry records in insertion order."""

    repository = InMemoryRetryRepository()
    first_record = _build_retry_record(
        migration_job_id="job-1",
        step_name="UploadItemsStep",
        attempt_number=1,
    )
    second_record = _build_retry_record(
        migration_job_id="job-1",
        step_name="UploadItemsStep",
        attempt_number=2,
    )
    other_job_record = _build_retry_record(
        migration_job_id="job-2",
        step_name="VerifyItemsStep",
        attempt_number=1,
    )

    assert repository.list_for_job("job-1") == []

    repository.save(first_record)
    repository.save(second_record)
    repository.save(other_job_record)

    assert repository.list_for_job("job-1") == [first_record, second_record]
    assert repository.list_for_job("job-2") == [other_job_record]


def test_in_memory_retry_repository_returns_copies_of_record_lists() -> None:
    """The repository should keep its internal storage isolated."""

    repository = InMemoryRetryRepository()
    record = _build_retry_record(
        migration_job_id="job-1",
        step_name="UploadItemsStep",
        attempt_number=1,
    )

    repository.save(record)
    loaded_records = repository.list_for_job("job-1")
    loaded_records.append(
        _build_retry_record(
            migration_job_id="job-1",
            step_name="UploadItemsStep",
            attempt_number=2,
        )
    )

    assert repository.list_for_job("job-1") == [record]


def test_in_memory_retry_repository_rejects_missing_job_identifier() -> None:
    """Retry records should require a migration job identifier."""

    repository = InMemoryRetryRepository()
    record = RetryRecord(
        id=RetryRecordId(value=UUID(int=1)),
        migration_item_id=None,
        retry_strategy=RetryStrategy.NONE,
        attempt_number=1,
    )

    with pytest.raises(ValueError):
        repository.save(record)
