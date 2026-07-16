"""In-memory retry repository adapter module.

This module provides a concrete in-memory implementation of the retry
repository port for development and testing. The repository stores immutable
retry records directly in memory and keeps the persistence boundary free of
filesystem, database, and orchestration concerns.
"""

from __future__ import annotations

from domain.entities import RetryRecord
from ports import RetryRepositoryPort


class InMemoryRetryRepository(RetryRepositoryPort):
    """Store retry records in an isolated in-memory dictionary."""

    __slots__ = ("_retry_records_by_job",)

    def __init__(self) -> None:
        """Create an empty in-memory retry repository."""

        self._retry_records_by_job: dict[str, list[RetryRecord]] = {}

    def save(self, retry_record: RetryRecord) -> None:
        """Store a retry record in insertion order for its migration job."""

        if retry_record.migration_job_id is None:
            message = "Retry records require a migration_job_id."
            raise ValueError(message)

        retry_records = self._retry_records_by_job.setdefault(
            retry_record.migration_job_id,
            [],
        )
        retry_records.append(retry_record)

    def list_for_job(self, job_id: str) -> list[RetryRecord]:
        """Return the retry records for a migration job in save order."""

        return list(self._retry_records_by_job.get(job_id, ()))


__all__: list[str] = ["InMemoryRetryRepository"]
