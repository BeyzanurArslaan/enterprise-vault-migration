"""Regression tests for retry-enabled pipeline execution."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from itertools import count

from adapters.database import InMemoryCheckpointRepository, InMemoryRetryRepository
from application.services import CheckpointService
from domain.enums.retry_strategy import RetryStrategy
from migration_engine.checkpoint import CheckpointSnapshot
from migration_engine.contracts import ExecutionContext, ExecutionReport, PipelineStep
from migration_engine.metrics import MigrationMetrics
from migration_engine.retry import RetryPolicy
from migration_engine.runner import PipelineRunner
from migration_engine.state_machine import MigrationState
from migration_engine.step_context import MigrationStepContext
from mock_storionx.exceptions import ServiceUnavailableError, TooManyRequestsError
from ports.identifier_generator_port import IdentifierGeneratorPort


def _build_metrics(
    *,
    total_items: int,
    processed_items: int,
    successful_items: int,
    failed_items: int,
    skipped_items: int,
    retried_items: int = 0,
) -> MigrationMetrics:
    """Create deterministic metrics for retry flow tests."""

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
        retried_items=retried_items,
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
    """Create a deterministic execution report for retry flow tests."""

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
    """Return predictable identifiers for retry flow tests."""

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
    """Provide deterministic timestamps for retry flow tests."""

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
        initial_context: MigrationStepContext | None = None,
    ) -> None:
        """Create a runner with deterministic timestamps and optional retry hooks."""

        super().__init__(
            steps,
            checkpoint_service=checkpoint_service,
            retry_policy=retry_policy,
            retry_repository=retry_repository,
            retry_classifier=retry_classifier,
            sleeper=sleeper,
            identifier_generator=identifier_generator,
            initial_context=initial_context,
        )
        self._timestamps = timestamps

    def _current_timestamp(self) -> datetime:
        """Return the next deterministic orchestration timestamp."""

        return next(self._timestamps)


class RetryableStep(PipelineStep):
    """Record lifecycle calls and fail deterministically for a set number of attempts."""

    def __init__(
        self,
        report: ExecutionReport,
        *,
        fail_attempts: int = 0,
        fail_message: str = "transient failure",
    ) -> None:
        """Create a retryable step with a deterministic failure plan."""

        self._report = report
        self._fail_attempts = fail_attempts
        self._fail_message = fail_message
        self._attempts = 0
        self.calls: list[str] = []

    def prepare(self, context: ExecutionContext) -> None:
        """Record the prepare call for the current attempt."""

        assert context.state is not None
        self.calls.append(f"prepare:{context.current_step}:{context.state.value}")

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Record the execute call and optionally raise a transient error."""

        assert context.state is not None
        self._attempts += 1
        self.calls.append(f"execute:{self._attempts}:{context.current_step}:{context.state.value}")
        if self._attempts <= self._fail_attempts:
            raise RuntimeError(self._fail_message)

        return self._report

    def finalize(self, context: ExecutionContext) -> None:
        """Record the finalize call for a successful attempt."""

        assert context.state is not None
        self.calls.append(f"finalize:{context.current_step}:{context.state.value}")

    def rollback(self, context: ExecutionContext) -> None:
        """Record the rollback call after a terminal failure."""

        assert context.state is not None
        self.calls.append(f"rollback:{context.current_step}:{context.state.value}")


class ReportingStep(PipelineStep):
    """Return a structural failure report without raising an exception."""

    def __init__(self, report: ExecutionReport) -> None:
        """Create a reporting step that never raises."""

        self._report = report
        self.calls: list[str] = []

    def prepare(self, context: ExecutionContext) -> None:
        """Record the prepare call for the step."""

        assert context.state is not None
        self.calls.append(f"prepare:{context.current_step}:{context.state.value}")

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Return the configured structural report."""

        assert context.state is not None
        self.calls.append(f"execute:{context.current_step}:{context.state.value}")
        return self._report

    def finalize(self, context: ExecutionContext) -> None:
        """Record the finalize call for the step."""

        assert context.state is not None
        self.calls.append(f"finalize:{context.current_step}:{context.state.value}")

    def rollback(self, context: ExecutionContext) -> None:
        """Record the rollback call for the step."""

        assert context.state is not None
        self.calls.append(f"rollback:{context.current_step}:{context.state.value}")


class TransportFailureStep(PipelineStep):
    """Raise a transient transport-style failure before succeeding."""

    def __init__(
        self,
        report: ExecutionReport,
        *,
        exception_factory: Callable[[], Exception],
        fail_attempts: int = 1,
    ) -> None:
        """Create a step that simulates a transient target failure."""

        self._report = report
        self._exception_factory = exception_factory
        self._fail_attempts = fail_attempts
        self._attempts = 0
        self.calls: list[str] = []

    def prepare(self, context: ExecutionContext) -> None:
        """Record the prepare call for the current attempt."""

        assert context.state is not None
        self.calls.append(f"prepare:{context.current_step}:{context.state.value}")

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Raise a transient failure before eventually succeeding."""

        assert context.state is not None
        self._attempts += 1
        self.calls.append(f"execute:{self._attempts}:{context.current_step}:{context.state.value}")
        if self._attempts <= self._fail_attempts:
            raise self._exception_factory()

        return self._report

    def finalize(self, context: ExecutionContext) -> None:
        """Record the finalize call for the step."""

        assert context.state is not None
        self.calls.append(f"finalize:{context.current_step}:{context.state.value}")

    def rollback(self, context: ExecutionContext) -> None:
        """Record the rollback call for the step."""

        assert context.state is not None
        self.calls.append(f"rollback:{context.current_step}:{context.state.value}")


class _RecordingCheckpointRepository(InMemoryCheckpointRepository):
    """Count checkpoint saves while keeping the concrete repository behavior."""

    def __init__(self) -> None:
        """Create a recording checkpoint repository."""

        super().__init__()
        self.save_calls = 0

    def save_checkpoint(self, checkpoint: CheckpointSnapshot) -> None:
        """Count checkpoint saves before delegating to the in-memory repository."""

        self.save_calls += 1
        super().save_checkpoint(checkpoint)


def _timestamp_sequence() -> Iterator[datetime]:
    """Yield deterministic timestamps for retry tests."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for offset in count():
        yield started_at + timedelta(seconds=offset)


def _build_success_report() -> ExecutionReport:
    """Create a successful step report for retry tests."""

    return _build_report(
        successful_steps=1,
        failed_steps=0,
        skipped_steps=0,
        total_items=1,
        processed_items=1,
        successful_items=1,
        failed_items=0,
        skipped_items=0,
    )


def _build_structural_failure_report() -> ExecutionReport:
    """Create a structural failure report without raising exceptions."""

    return _build_report(
        successful_steps=1,
        failed_steps=0,
        skipped_steps=0,
        total_items=1,
        processed_items=1,
        successful_items=0,
        failed_items=1,
        skipped_items=0,
    )


def test_pipeline_runner_without_retry_policy_preserves_current_behavior() -> None:
    """The runner should keep the existing failure path when retries are disabled."""

    step = RetryableStep(_build_success_report(), fail_attempts=1)
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is False
    assert result.errors == ("transient failure",)
    assert step.calls == [
        "prepare:RetryableStep:initializing",
        "execute:1:RetryableStep:initializing",
        "rollback:RetryableStep:failed",
    ]
    assert runner.state_machine.current_state == MigrationState.FAILED
    assert runner.metrics is not None
    assert runner.metrics.retried_items == 0


def test_pipeline_runner_does_not_retry_non_retryable_failure() -> None:
    """A configured policy should still skip retries for non-retryable failures."""

    delays: list[float] = []
    retry_repository = InMemoryRetryRepository()
    step = RetryableStep(_build_success_report(), fail_attempts=1)
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=3,
            fixed_delay_seconds=2.5,
        ),
        retry_repository=retry_repository,
        retry_classifier=lambda _exception: False,
        sleeper=delays.append,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is False
    assert delays == []
    assert retry_repository.list_for_job("migration-1") == []
    assert step.calls == [
        "prepare:RetryableStep:initializing",
        "execute:1:RetryableStep:initializing",
        "rollback:RetryableStep:failed",
    ]


def test_pipeline_runner_none_strategy_does_not_retry() -> None:
    """The none strategy should prevent retry execution at the runner boundary."""

    delays: list[float] = []
    retry_repository = InMemoryRetryRepository()
    step = RetryableStep(_build_success_report(), fail_attempts=1)
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        retry_policy=RetryPolicy(strategy=RetryStrategy.NONE, max_attempts=3),
        retry_repository=retry_repository,
        retry_classifier=lambda _exception: True,
        sleeper=delays.append,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is False
    assert delays == []
    assert retry_repository.list_for_job("migration-1") == []
    assert step.calls == [
        "prepare:RetryableStep:initializing",
        "execute:1:RetryableStep:initializing",
        "rollback:RetryableStep:failed",
    ]


def test_pipeline_runner_retries_transient_failure_and_persists_retry_records() -> None:
    """The runner should retry a transient failure and persist the retry record."""

    delays: list[float] = []
    retry_repository = InMemoryRetryRepository()
    step = RetryableStep(_build_success_report(), fail_attempts=1)
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=3,
            fixed_delay_seconds=2.5,
        ),
        retry_repository=retry_repository,
        retry_classifier=lambda exception: isinstance(exception, RuntimeError),
        sleeper=delays.append,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is True
    assert delays == [2.5]
    assert runner.metrics is not None
    assert runner.metrics.retried_items == 1
    assert len(retry_repository.list_for_job("migration-1")) == 1
    assert retry_repository.list_for_job("migration-1")[0].attempt_number == 1
    assert retry_repository.list_for_job("migration-1")[0].pipeline_step_name == "RetryableStep"
    assert step.calls == [
        "prepare:RetryableStep:initializing",
        "execute:1:RetryableStep:initializing",
        "prepare:RetryableStep:initializing",
        "execute:2:RetryableStep:initializing",
        "finalize:RetryableStep:initializing",
    ]


def test_pipeline_runner_recovers_from_retry_after_throttling() -> None:
    """429-style throttling should retry with retry-after awareness."""

    delays: list[float] = []
    retry_repository = InMemoryRetryRepository()
    step = TransportFailureStep(
        _build_success_report(),
        exception_factory=lambda: TooManyRequestsError(retry_after_seconds=1.5),
    )
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=3,
            fixed_delay_seconds=0.25,
        ),
        retry_repository=retry_repository,
        sleeper=delays.append,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is True
    assert delays == [1.5]
    assert runner.metrics is not None
    assert runner.metrics.throttled_uploads == 1
    assert runner.metrics.retry_after_count == 1
    assert runner.metrics.temporary_failures == 0
    assert runner.metrics.retried_items == 1
    assert len(retry_repository.list_for_job("migration-1")) == 1
    assert retry_repository.list_for_job("migration-1")[0].attempt_number == 1
    assert step.calls == [
        "prepare:TransportFailureStep:initializing",
        "execute:1:TransportFailureStep:initializing",
        "prepare:TransportFailureStep:initializing",
        "execute:2:TransportFailureStep:initializing",
        "finalize:TransportFailureStep:initializing",
    ]


def test_pipeline_runner_recovers_from_temporary_service_unavailability() -> None:
    """503-style temporary outages should increment failure metrics and retry."""

    delays: list[float] = []
    retry_repository = InMemoryRetryRepository()
    step = TransportFailureStep(
        _build_success_report(),
        exception_factory=lambda: ServiceUnavailableError(),
    )
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=3,
            fixed_delay_seconds=0.25,
        ),
        retry_repository=retry_repository,
        sleeper=delays.append,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is True
    assert delays == [0.25]
    assert runner.metrics is not None
    assert runner.metrics.throttled_uploads == 0
    assert runner.metrics.retry_after_count == 0
    assert runner.metrics.temporary_failures == 1
    assert runner.metrics.retried_items == 1
    assert len(retry_repository.list_for_job("migration-1")) == 1


def test_pipeline_runner_uses_exponential_backoff_delay_sequence() -> None:
    """The runner should apply deterministic exponential retry delays."""

    delays: list[float] = []
    retry_repository = InMemoryRetryRepository()
    step = RetryableStep(_build_success_report(), fail_attempts=2)
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_attempts=4,
            initial_backoff_seconds=1.0,
            maximum_backoff_seconds=10.0,
            backoff_multiplier=2.0,
        ),
        retry_repository=retry_repository,
        retry_classifier=lambda exception: isinstance(exception, RuntimeError),
        sleeper=delays.append,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is True
    assert delays == [1.0, 2.0]
    assert len(retry_repository.list_for_job("migration-1")) == 2
    assert [record.attempt_number for record in retry_repository.list_for_job("migration-1")] == [
        1,
        2,
    ]


def test_pipeline_runner_stops_retrying_after_max_attempt_exhaustion() -> None:
    """The runner should fail after the retry policy exhausts all attempts."""

    delays: list[float] = []
    retry_repository = InMemoryRetryRepository()
    step = RetryableStep(_build_success_report(), fail_attempts=3)
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=2,
            fixed_delay_seconds=1.0,
        ),
        retry_repository=retry_repository,
        retry_classifier=lambda exception: isinstance(exception, RuntimeError),
        sleeper=delays.append,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is False
    assert result.errors == ("transient failure",)
    assert delays == [1.0]
    assert len(retry_repository.list_for_job("migration-1")) == 1
    assert runner.state_machine.current_state == MigrationState.FAILED
    assert runner.metrics is not None
    assert runner.metrics.retried_items == 1
    assert any(call.startswith("rollback:RetryableStep:failed") for call in step.calls)


def test_pipeline_runner_does_not_retry_structural_failure_reports() -> None:
    """Structural item-level failures should not trigger a whole-step retry."""

    delays: list[float] = []
    retry_repository = InMemoryRetryRepository()
    step = ReportingStep(_build_structural_failure_report())
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=3,
            fixed_delay_seconds=1.0,
        ),
        retry_repository=retry_repository,
        retry_classifier=lambda exception: isinstance(exception, RuntimeError),
        sleeper=delays.append,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is True
    assert result.execution_report is not None
    assert result.execution_report.metrics is not None
    assert result.execution_report.metrics.failed_items == 1
    assert delays == []
    assert retry_repository.list_for_job("migration-1") == []
    assert step.calls == [
        "prepare:ReportingStep:initializing",
        "execute:ReportingStep:initializing",
        "finalize:ReportingStep:initializing",
    ]


def test_pipeline_runner_saves_checkpoint_only_after_eventual_success() -> None:
    """A checkpoint should be saved only after a step eventually succeeds."""

    checkpoint_repository = _RecordingCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=checkpoint_repository)
    step = RetryableStep(_build_success_report(), fail_attempts=1)
    runner = _DeterministicPipelineRunner(
        steps=(step,),
        timestamps=_timestamp_sequence(),
        checkpoint_service=checkpoint_service,
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=3,
            fixed_delay_seconds=1.0,
        ),
        retry_classifier=lambda exception: isinstance(exception, RuntimeError),
        sleeper=lambda _delay: None,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is True
    assert checkpoint_repository.save_calls == 1
    checkpoint = checkpoint_repository.load_checkpoint("migration-1")
    assert checkpoint is not None
    assert checkpoint.last_completed_step == "RetryableStep"
    assert checkpoint.current_state == MigrationState.INITIALIZING.value
    assert runner.current_step_context is not None
    assert runner.current_step_context.checkpoint == checkpoint


def test_pipeline_runner_preserves_previous_checkpoint_when_retries_exhaust() -> None:
    """The runner should keep the last valid checkpoint if retries fail."""

    checkpoint_repository = _RecordingCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=checkpoint_repository)
    first_step = ReportingStep(_build_success_report())
    second_step = RetryableStep(_build_success_report(), fail_attempts=3)
    runner = _DeterministicPipelineRunner(
        steps=(first_step, second_step),
        timestamps=_timestamp_sequence(),
        checkpoint_service=checkpoint_service,
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=2,
            fixed_delay_seconds=1.0,
        ),
        retry_classifier=lambda exception: isinstance(exception, RuntimeError),
        sleeper=lambda _delay: None,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = runner.run()

    assert result.success is False
    assert checkpoint_repository.save_calls == 1
    checkpoint = checkpoint_repository.load_checkpoint("migration-1")
    assert checkpoint is not None
    assert checkpoint.last_completed_step == "ReportingStep"
    assert checkpoint.current_state == MigrationState.INITIALIZING.value
    assert runner.state_machine.current_state == MigrationState.FAILED
    assert runner.current_step_context is not None
    assert any(call.startswith("rollback:RetryableStep:failed") for call in second_step.calls)


def test_pipeline_runner_remains_compatible_with_resume_and_retries() -> None:
    """A resumed migration should continue to honor retry execution."""

    checkpoint_repository = _RecordingCheckpointRepository()
    checkpoint_service = CheckpointService(checkpoint_repository=checkpoint_repository)
    first_step = ReportingStep(_build_success_report())
    second_step = RetryableStep(_build_success_report(), fail_attempts=1)

    partial_runner = _DeterministicPipelineRunner(
        steps=(first_step,),
        timestamps=_timestamp_sequence(),
        checkpoint_service=checkpoint_service,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )
    partial_runner.run()
    resume_checkpoint = checkpoint_repository.load_checkpoint("migration-1")
    assert resume_checkpoint is not None

    resumed_runner = _DeterministicPipelineRunner(
        steps=(first_step, second_step),
        timestamps=_timestamp_sequence(),
        checkpoint_service=checkpoint_service,
        retry_policy=RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=3,
            fixed_delay_seconds=1.0,
        ),
        retry_classifier=lambda exception: isinstance(exception, RuntimeError),
        sleeper=lambda _delay: None,
        identifier_generator=_DeterministicIdentifierGenerator(),
    )

    result = resumed_runner.run(resume_checkpoint=resume_checkpoint)

    assert result.success is True
    assert resumed_runner.current_step_context is not None
    assert resumed_runner.current_step_context.checkpoint is not None
    assert resumed_runner.current_step_context.checkpoint.last_completed_step == "RetryableStep"
