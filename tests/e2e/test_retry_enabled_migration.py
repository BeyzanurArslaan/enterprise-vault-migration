"""End-to-end regression tests for retry-enabled migration execution."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from itertools import count

from adapters.database import InMemoryCheckpointRepository, InMemoryRetryRepository
from application.services import CheckpointService
from domain.enums.retry_strategy import RetryStrategy
from migration_engine.contracts import ExecutionContext, ExecutionReport, PipelineStep
from migration_engine.metrics import MigrationMetrics
from migration_engine.retry import RetryPolicy
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState
from ports.identifier_generator_port import IdentifierGeneratorPort


def _build_metrics(
    *,
    total_items: int,
    processed_items: int,
    successful_items: int,
    failed_items: int,
    skipped_items: int,
) -> MigrationMetrics:
    """Create deterministic metrics for end-to-end retry tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return MigrationMetrics(
        duration_seconds=1.0,
        throughput_items_per_second=1.0,
        average_item_size=1024,
        processed_bytes=2048,
        estimated_remaining_seconds=None,
        peak_memory_usage_mb=None,
        total_items=total_items,
        processed_items=processed_items,
        successful_items=successful_items,
        failed_items=failed_items,
        skipped_items=skipped_items,
        retried_items=0,
        uploaded_items=successful_items,
        verification_failures=failed_items,
        total_bytes=4096,
        started_at=timestamp,
        finished_at=timestamp,
    )


def _build_report(
    *,
    successful_steps: int,
    failed_steps: int,
    skipped_steps: int,
    total_items: int,
    processed_items: int,
    successful_items: int,
    failed_items: int,
    skipped_items: int,
) -> ExecutionReport:
    """Create a deterministic execution report for end-to-end tests."""

    return ExecutionReport(
        successful_steps=successful_steps,
        failed_steps=failed_steps,
        skipped_steps=skipped_steps,
        duration_seconds=1.0,
        completed=True,
        metrics=_build_metrics(
            total_items=total_items,
            processed_items=processed_items,
            successful_items=successful_items,
            failed_items=failed_items,
            skipped_items=skipped_items,
        ),
    )


class _DeterministicIdentifierGenerator(IdentifierGeneratorPort):
    """Return predictable identifiers for end-to-end retry tests."""

    def next_archive_id(self) -> str:
        """Return a deterministic archive identifier."""

        return "archive-1"

    def next_mail_item_id(self) -> str:
        """Return a deterministic mail item identifier."""

        return "mail-item-1"

    def next_attachment_id(self) -> str:
        """Return a deterministic attachment identifier."""

        return "attachment-1"

    def next_archived_file_id(self) -> str:
        """Return a deterministic archived file identifier."""

        return "archived-file-1"

    def next_job_id(self) -> str:
        """Return a deterministic migration job identifier."""

        return "migration-1"

    def next_migration_item_id(self) -> str:
        """Return a deterministic migration item identifier."""

        return "migration-item-1"


class _DeterministicPipelineRunner(PipelineRunner):
    """Provide deterministic timestamps for end-to-end retry tests."""

    def __init__(
        self,
        *,
        steps: tuple[PipelineStep, ...],
        timestamps: Iterator[datetime],
        checkpoint_service: CheckpointService | None = None,
        retry_policy: RetryPolicy | None = None,
        retry_repository: InMemoryRetryRepository | None = None,
        retry_classifier: Callable[[Exception], bool] | None = None,
        sleeper: Callable[[float], None] | None = None,
        identifier_generator: IdentifierGeneratorPort | None = None,
    ) -> None:
        """Create a runner with deterministic timestamps and retry hooks."""

        super().__init__(
            steps,
            checkpoint_service=checkpoint_service,
            retry_policy=retry_policy,
            retry_repository=retry_repository,
            retry_classifier=retry_classifier,
            sleeper=sleeper,
            identifier_generator=identifier_generator,
        )
        self._timestamps = timestamps

    def _current_timestamp(self) -> datetime:
        """Return the next deterministic orchestration timestamp."""

        return next(self._timestamps)


class RetryableStep(PipelineStep):
    """Record lifecycle calls and fail once before succeeding."""

    def __init__(self, report: ExecutionReport, *, fail_attempts: int = 0) -> None:
        """Create a retryable step with a deterministic failure plan."""

        self._report = report
        self._fail_attempts = fail_attempts
        self._attempts = 0
        self.calls: list[str] = []

    def prepare(self, context: ExecutionContext) -> None:
        """Record the prepare call for the current attempt."""

        assert context.state is not None
        self.calls.append(f"prepare:{context.current_step}:{context.state.value}")

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Return the report after the configured number of transient failures."""

        assert context.state is not None
        self._attempts += 1
        self.calls.append(f"execute:{self._attempts}:{context.current_step}:{context.state.value}")
        if self._attempts <= self._fail_attempts:
            raise RuntimeError("transient failure")

        return self._report

    def finalize(self, context: ExecutionContext) -> None:
        """Record the finalize call for the current attempt."""

        assert context.state is not None
        self.calls.append(f"finalize:{context.current_step}:{context.state.value}")

    def rollback(self, context: ExecutionContext) -> None:
        """Record the rollback call when the run fails."""

        assert context.state is not None
        self.calls.append(f"rollback:{context.current_step}:{context.state.value}")


def _timestamp_sequence() -> Iterator[datetime]:
    """Yield deterministic timestamps for the end-to-end runner."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for offset in count():
        yield started_at + timedelta(seconds=offset)


def test_retry_enabled_migration_completes_with_retry_and_checkpoint() -> None:
    """The full pipeline should complete successfully with retry support enabled."""

    retry_repository = InMemoryRetryRepository()
    checkpoint_repository = InMemoryCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=checkpoint_repository)
    step = RetryableStep(
        _build_report(
            successful_steps=1,
            failed_steps=0,
            skipped_steps=0,
            total_items=1,
            processed_items=1,
            successful_items=1,
            failed_items=0,
            skipped_items=0,
        ),
        fail_attempts=1,
    )

    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        checkpoint_service=checkpoint_service,
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=3,
            fixed_delay_seconds=1.0,
        ),
        retry_repository=retry_repository,
        retry_classifier=lambda exception: isinstance(exception, RuntimeError),
        sleeper=lambda _delay: None,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is True
    assert runner.state_machine.current_state == MigrationState.COMPLETED
    assert checkpoint_repository.load_checkpoint("migration-1") is not None
    assert len(retry_repository.list_for_job("migration-1")) == 1
    assert step.calls == [
        "prepare:RetryableStep:initializing",
        "execute:1:RetryableStep:initializing",
        "prepare:RetryableStep:initializing",
        "execute:2:RetryableStep:initializing",
        "finalize:RetryableStep:initializing",
    ]
