# Enterprise Vault Migration

A deterministic, target-neutral migration engine for moving archived Veritas Enterprise Vault content into storionX-compatible target storage.

## 1. Overview

`enterprise-vault-migration` is an end-to-end migration simulation for transferring archived content from Veritas Enterprise Vault to storionX.

The repository is designed as a migration orchestration platform rather than a CRUD application. It coordinates:

- archive discovery
- source filtering
- item extraction
- SIS rehydration
- transformation
- target upload
- verification
- reconciliation
- retry handling
- checkpoint and resume
- reporting
- JSON and CSV export

The current Enterprise Vault and storionX integrations are deterministic mock implementations. They allow migration behavior, architectural boundaries, error handling, idempotency, and recovery scenarios to be tested without requiring access to real Enterprise Vault or storionX environments.

The migration engine depends on abstract ports instead of concrete source and target implementations. Production adapters can therefore replace the mock adapters without rewriting the core migration orchestration layer.

The architecture is designed to evolve toward production integrations, while the current repository remains a deterministic, in-memory simulation.

---

## 2. Assignment Coverage

The repository covers the main requirements of the Enterprise Vault to storionX migration assignment.

| Assignment area | Repository coverage |
|---|---|
| Enterprise Vault analysis | Models mailbox, journal, orphaned, legal-hold, departed-user, SIS, shortcut, and FSA-related concepts |
| Mock Enterprise Vault | Provides deterministic source archives, archived items, metadata, attachments, SIS references, orphaned archives, and unsupported FSA scenarios |
| Mock storionX | Provides in-memory ingestion, metadata storage, lookup, verification, idempotency, throttling, and transient failure simulation |
| Discovery | Discovers archives and migration scope through the Enterprise Vault source port |
| Identity mapping | Applies deterministic logical mapping through source contracts and transformation policies |
| Extraction | Extracts source items into engine-level runtime contracts |
| SIS rehydration | Reconstructs SIS-backed content through source-neutral interfaces |
| Transformation | Produces target-neutral transformed documents |
| Upload | Uploads transformed documents through the storionX target port |
| Retry | Supports deterministic fixed-delay and exponential-backoff retry behavior |
| Rate limiting | Simulates target throughput limits and retry-after behavior |
| 429 handling | Models deterministic throttling through a target-side exception |
| 503 handling | Models deterministic, injectable temporary service failures |
| Parallel upload | Uses bounded single-process worker concurrency |
| Idempotency | Prevents duplicate target creation by stable source identifier |
| Verification | Compares uploaded identifiers, checksums, and essential metadata |
| Reconciliation | Compares expected source results with observed target results |
| Checkpoint/resume | Saves minimal continuation state and resumes completed jobs |
| Dry run | Executes migration flow without target mutation |
| Filters | Supports archive, folder, start-date, and end-date filtering |
| Reporting | Produces immutable execution reports, metrics, warnings, and errors |
| JSON export | Serializes structured reports deterministically |
| CSV export | Produces audit-oriented error exports with spreadsheet formula protection |
| Unit testing | Covers isolated policies, services, adapters, and pipeline components |
| Integration testing | Covers interactions between application, engine, ports, and adapters |
| End-to-end testing | Exercises the complete mock EV-to-storionX migration flow |

### Explicit scope boundaries

The following capabilities are not implemented:

- production Enterprise Vault SDK integration
- live Enterprise Vault SQL catalog integration
- live storionX REST API integration
- full FSA file-content migration
- SharePoint migration
- source-side shortcut cleanup
- PST or ZIP legal-export package generation
- durable database-backed checkpoint storage
- durable retry storage
- distributed worker coordination
- production full-text search
- production authentication, authorization, or TLS

FSA archives are modeled and remain visible in discovery and reporting, but full FSA file-content migration follows an explicit unsupported-policy path.

---

## 3. Key Features

- Clean Architecture
- Hexagonal Ports and Adapters
- DDD-inspired domain model
- SOLID-oriented boundaries
- source-neutral and target-neutral contracts
- immutable runtime dataclasses
- strict typing
- deterministic execution
- deterministic mock data generation
- mock Enterprise Vault source adapter
- mock storionX target adapter
- mailbox and journal migration scenarios
- orphaned archive handling
- departed-user and legal-hold metadata preservation
- FSA unsupported-policy handling
- SIS content rehydration
- execution-scoped SIS caching
- checksum and metadata preservation
- bounded parallel upload
- execution-scoped rate limiting
- deterministic 429-style throttling
- deterministic 503-style service failures
- centralized retry orchestration
- target-authoritative idempotency
- checkpoint and resume
- dry-run execution
- archive, folder, and date filters
- post-upload verification
- source-to-target reconciliation
- JSON report export
- CSV error export
- structured error breakdown
- item-level failure isolation
- unit, integration, and end-to-end tests

---

## 4. Supported Migration Scenarios

### Mailbox Archives

Mailbox migrations preserve migration-relevant email information such as:

- mailbox and owner identity
- archive identifier
- folder path
- message subject
- sender
- recipients
- CC and BCC recipients
- original timestamps
- attachments
- retention metadata
- legal-hold metadata
- source identifier
- checksum
- custom properties

Mailbox content can be filtered by archive, folder, and date range before transformation and upload.

### Journal Archives

Journal archives are handled independently from normal mailbox ownership.

The migration flow preserves:

- journal archive identity
- compliance context
- sender and recipient metadata
- envelope-related metadata where modeled
- original timestamps
- SIS-backed content
- checksum
- retention metadata
- legal-hold metadata
- journal-specific custom properties

Journal items can be mapped to a logical storionX compliance destination without requiring an active mailbox owner.

### Orphaned Archives

An archive is treated as orphaned when its stable Enterprise Vault archive identifier is known but no active owner can be resolved.

The orphaned archive policy ensures that:

- the archive remains discoverable
- no fake active owner is created
- the original owner is preserved when available
- unresolved ownership remains explicit
- supported content may continue through migration
- orphan state remains visible in transformed metadata and reports

### Departed Users and Legal Hold

Departed-user archives continue to use their stable source archive identity.

The migration preserves:

- original mailbox or owner metadata
- original archive identity
- folder and source paths
- timestamps
- checksums
- retention policies
- legal-hold flags
- legal-hold policy identifiers where available
- verification and reconciliation evidence

Legal hold is treated as a compliance state that is separate from normal retention duration. It is not modeled as an artificially long retention period.

The repository does not generate PST, ZIP, or other physical legal-export packages.

### FSA Archives

File System Archiving is structurally represented in the source domain.

The current implementation:

- discovers FSA archives
- preserves source archive identity
- preserves source-path metadata
- classifies unsupported FSA content explicitly
- exposes unsupported FSA items in warnings and reporting
- allows unrelated mailbox and journal content to continue

Full FSA file-content extraction and migration are not implemented.

### Mixed Migrations

A single migration execution may contain multiple archive and item types.

Failure isolation allows supported items to continue when another item:

- is unsupported
- fails transformation
- is throttled
- exhausts retries
- fails verification
- produces a reconciliation mismatch

---

## 5. Architecture

The repository follows Clean Architecture, Hexagonal Architecture, and DDD-inspired boundaries.

```text
Application / Use Cases
          ↓
Migration Engine
          ↓
Ports
          ↓
Adapters
          ↓
Mock Enterprise Vault / mock storionX
```

Dependencies point inward.

The domain and migration engine do not depend on mock infrastructure. Source access, target access, checkpoint persistence, retry persistence, clock access, logging, configuration, identifier generation, and checksum calculation are exposed through ports.

Adapters translate between engine contracts and implementation-specific models.

This structure allows the current mock adapters to be replaced by production implementations without moving infrastructure logic into the migration engine.

Reports are generated from immutable structured runtime results rather than by parsing application logs.

See [DESIGN.md](DESIGN.md) for detailed migration scenarios, component flows, architectural decisions, security, scalability, and known limitations.

---

## 6. Migration Pipeline

The logical migration flow is:

```text
Discovery
  → Logical Mapping
  → Extraction
  → SIS Rehydration
  → Transformation
  → Upload
  → Verification
  → Reconciliation
  → Reporting
```

### Discovery

Discovers Enterprise Vault archives and identifies the migration scope.

### Logical Mapping

Determines the logical destination for mailbox, journal, orphaned, and other supported archive scenarios.

Logical mapping is expressed through source contracts, transformation rules, and adapter behavior. It is not required to exist as a standalone registered pipeline step.

### Extraction

Reads migration-relevant archive and item information from the source adapter and produces engine-level extraction results.

### SIS Rehydration

Reconstructs SIS-backed content using source-neutral SIS part contracts.

SIS rehydration is integrated into pipeline orchestration and may be performed as part of transformation processing rather than as a separately registered deployment component.

### Transformation

Converts extracted source data into immutable, target-neutral transformed documents.

### Upload

Uploads transformed documents through the storionX target port using bounded workers, target-side rate limiting, retry handling, and idempotency.

### Verification

Reads uploaded target documents through the target port and compares stable identifiers, checksums, and essential metadata.

### Reconciliation

Compares expected source outcomes against observed target outcomes.

### Reporting

Builds structured reports, metrics, warnings, reconciliation information, and exportable error breakdowns.

---

## 7. Repository Structure

```text
.
├── DESIGN.md
├── README.md
├── LICENSE
├── pyproject.toml
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── config/
├── data/
├── docs/
├── examples/
├── scripts/
├── src/
│   ├── application/
│   ├── domain/
│   ├── ports/
│   ├── adapters/
│   ├── migration_engine/
│   ├── mock_ev/
│   └── mock_storionx/
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

### Main directories

- `src/domain/`: domain entities, value objects, identifiers, enums, and exceptions.
- `src/application/`: commands, use cases, services, DTOs, queries, and orchestration entry points.
- `src/ports/`: abstract interfaces for source, target, persistence, clock, logging, configuration, identifiers, and checksum behavior.
- `src/adapters/`: concrete adapters that connect engine ports to mock and in-memory implementations.
- `src/migration_engine/`: pipeline contracts, steps, runner, state, metrics, retry, checkpoint, verification, reconciliation, and reporting behavior.
- `src/mock_ev/`: deterministic Enterprise Vault source models, fixtures, services, and generators.
- `src/mock_storionx/`: deterministic storionX target models, storage, rate limiting, transient failures, and idempotency behavior.
- `tests/unit/`: isolated tests for domain, policies, services, steps, and adapters.
- `tests/integration/`: tests across multiple architectural layers.
- `tests/e2e/`: complete migration-flow tests using mock source and target implementations.
- `docs/`: supplementary design, architecture, ADR, API, report, and diagram material.
- `examples/`: project usage examples where provided.
- `scripts/`: repository utility scripts where provided.
- `config/`: project configuration samples or support files.
- `data/`: local mock or generated data artifacts where used.

---

## 8. Requirements

The project requires:

- Python 3.12 or later
- `pip`
- Git

Development tooling includes:

- Ruff
- Black
- MyPy
- Pytest
- pytest-cov
- Coverage
- pre-commit

The current implementation does not require:

- a running Enterprise Vault environment
- a running storionX environment
- an external database
- a message broker
- cloud infrastructure
- a production secrets manager

All default development and test behavior is based on deterministic mock and in-memory adapters.

Docker-related files are included for repository packaging and local environment support, but the core test suite can run directly in a Python virtual environment.

---

## 9. Installation

Clone the repository:

```bash
git clone <your-repository-url>
cd enterprise-vault-migration
```

Create and activate a Python 3.12 virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Upgrade packaging tools:

```bash
python -m pip install --upgrade pip
```

Install the project and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Verify the installation:

```bash
python -m compileall src
pytest -q
```

---

## 10. Quick Start

The repository currently exposes migration behavior through application services, adapters, and automated tests rather than through a packaged command-line interface.

Run the complete test suite:

```bash
pytest -q
```

Run the end-to-end migration tests:

```bash
pytest -q tests/e2e
```

Run integration tests:

```bash
pytest -q tests/integration
```

Run unit tests:

```bash
pytest -q tests/unit
```

Run tests with warnings treated as errors:

```bash
pytest -W error
```

The end-to-end tests demonstrate the real application wiring used by the repository, including:

- mock EV archive discovery
- source extraction
- SIS rehydration
- transformation
- upload
- retry
- idempotency
- checkpointing
- verification
- reconciliation
- reporting

No external Enterprise Vault or storionX system is required.

---

## 11. Configuration

Migration behavior is configured through immutable application and migration-engine configuration objects.

Configuration is primarily supplied programmatically. The repository does not require environment-variable-driven configuration for the core in-memory migration flow.

### Execution Options

Execution configuration may include:

- migration job identity
- dry-run mode
- checkpoint behavior
- resume state
- execution timestamps
- runtime scope

### Filtering Options

The implemented source filters cover:

- archive names
- folder paths
- start date
- end date

Filter values remain part of the execution scope and are preserved in checkpoints and reports.

### Retry Options

Retry behavior includes:

- retry strategy
- maximum attempt count
- retry delay
- maximum retry delay
- retry classification
- retry history when a retry repository is configured

Supported retry strategies include:

- no retry
- fixed delay
- exponential backoff

### Upload Options

Upload orchestration includes configuration for:

- bounded worker count
- requests-per-second rate limit
- target-side throttling behavior
- deterministic transient failures

### Checkpoint Options

Checkpoint behavior is exposed through a repository port.

The current development implementation uses an in-memory checkpoint repository. It supports checkpoint and resume behavior within the repository simulation but does not provide durable process-restart persistence.

A production deployment would provide a database-backed or durable checkpoint adapter.

---

## 12. Usage

The application layer coordinates migration commands, services, use cases, and the migration orchestrator.

The migration engine remains independent from concrete Enterprise Vault and storionX implementations.

### Running a Migration

A migration run consists conceptually of:

1. constructing the source adapter
2. constructing the target adapter
3. constructing required repositories and services
4. creating immutable migration configuration
5. invoking the application orchestrator or migration service
6. receiving an immutable execution result and report

The repository’s end-to-end tests provide the authoritative executable examples for complete dependency wiring.

Run them with:

```bash
pytest -q tests/e2e
```

### Running a Dry Run

Dry-run behavior is enabled through migration configuration.

A dry run:

- executes discovery and processing logic
- applies filters
- records dry-run counts
- avoids target mutation
- produces structured reporting

### Applying Filters

Source scope may be limited by:

- archive name
- folder path
- start date
- end date

Filtered items are not treated as migration failures.

### Configuring Retry

Retry configuration controls:

- strategy
- total attempts
- fixed or exponential delay
- maximum delay
- retryable failure classification

Attempt `1` is always the initial execution.

### Configuring Parallel Upload

Bounded parallel upload is controlled through migration configuration and target adapter construction.

The configured worker count limits concurrent upload work within one process.

### Resuming from a Checkpoint

Resume behavior loads the latest valid checkpoint, validates it, reconstructs continuation context, and resumes after already completed work.

### Exporting Reports

The reporting package provides deterministic JSON and CSV serialization helpers.

Exporters produce serialized output from immutable report contracts. They do not imply automatic file persistence unless called by an external application layer.

---

## 13. Dry Run

Dry run is a first-class migration mode.

When dry run is enabled:

- the source is still discovered
- filters are still applied
- extraction and transformation behavior can still be exercised
- target mutation is skipped
- dry-run item counts are tracked
- checkpoints remain structurally compatible
- reports are still generated
- skipped uploads are not classified as failures

Dry run is not a separate migration engine. It uses the same orchestration flow with target mutation disabled.

---

## 14. Filtering

The migration scope can be restricted through source-side filters.

Supported filters include:

- archive names
- folder paths
- start date
- end date

Filtering occurs before target upload.

Filter state is preserved in:

- migration configuration
- execution context
- checkpoint snapshots
- final reports

This ensures that a resumed migration uses the same source scope as the original execution.

Filtered-out items are expected scope exclusions and are not treated as errors.

The target adapter does not interpret source filters.

---

## 15. SIS Rehydration

Enterprise Vault Single Instance Storage may store content parts once and allow multiple archived items to reference those parts.

The migration engine rehydrates SIS-backed content before final transformation.

Implemented behavior includes:

- SIS references exposed through source-neutral contracts
- ordered content-part reconstruction
- execution-scoped caching
- prevention of repeated reads during one execution
- checksum validation where represented
- size validation where represented
- deterministic rehydration failures
- structured failure reporting
- no source mutation

The SIS cache is scoped to one migration execution.

It is not:

- global state
- a durable cache
- a separate microservice
- shared across independent migration runs

Raw SIS payloads are not stored in checkpoints or reports.

---

## 16. Retry and Transient Failures

Retry behavior is deterministic and policy-driven.

### Attempt semantics

- Attempt `1` is the initial execution.
- `max_attempts` includes the initial attempt.
- Remaining attempts represent executions still available after the current attempt.

### Retry strategies

#### No Retry

The failure is returned immediately without another attempt.

#### Fixed Delay

Each retry waits for a deterministic constant delay.

#### Exponential Backoff

The retry delay increases exponentially and is capped by the configured maximum delay.

The current deterministic model does not require random jitter.

### 429-style throttling

The mock storionX target may signal target capacity pressure through a throttling error.

The error may include retry-after information.

The migration engine does not depend directly on HTTP response types. The adapter translates target behavior into retryable failure information that the retry subsystem can evaluate.

### 503-style temporary failures

The mock storionX target can inject deterministic temporary service failures.

The assignment may describe random transient failures, such as a 5% service-unavailable rate. The repository intentionally uses deterministic, injectable failure scenarios instead.

This provides equivalent retry and recovery coverage while keeping tests:

- reproducible
- debuggable
- stable
- independent from random seeds

### Retry exhaustion

When no attempts remain:

- the failure becomes terminal
- a structured error may be created
- retry metrics remain available
- unrelated items may continue when item-level failure isolation applies

A successful retry is not reported as a terminal error.

---

## 17. Rate Limiting and Parallel Upload

Rate limiting is implemented at the mock target boundary.

The upload rate limiter is:

- execution-scoped
- thread-safe
- deterministic
- configurable in requests per second
- free from global mutable state

The limiter returns retry-after information instead of sleeping internally. Retry timing remains coordinated by the migration engine.

### Bounded parallel upload

Uploads are processed with a configurable bounded worker pool.

The implementation preserves:

- predictable resource usage
- deterministic result ordering
- target-side idempotency
- shared rate-limit safety
- failure isolation
- structured reporting

Duplicate source identifiers are suppressed before upload fan-out where applicable.

The current implementation supports concurrency inside one process.

It does not implement:

- distributed workers
- queue-based work distribution
- cross-process leases
- cluster coordination
- distributed checkpoints

---

## 18. Idempotency

Idempotency is enforced at the target adapter boundary.

The stable idempotency key is:

```text
source_identifier
```

### First upload

The first upload for a source identifier creates one target document.

### Same-checksum replay

When the same source identifier is uploaded with the same checksum:

- the existing target document is reused
- the existing target identifier is returned
- the operation is classified as an idempotent replay
- no duplicate target document is created
- the replay is not treated as a failure

### Conflicting replay

When the same source identifier is uploaded with a different checksum:

- the target adapter raises an explicit idempotency conflict
- no duplicate record is created
- the conflict becomes visible through structured error handling

Idempotency belongs at the target boundary because the target is authoritative for determining whether content has already been ingested.

---

## 19. Checkpoint and Resume

Checkpointing stores the minimal state required to continue migration execution.

Checkpoint snapshots may include:

- migration job identifier
- completed step
- last processed source identifier
- execution state
- processed count
- successful count
- failed count
- skipped count
- uploaded count
- verification-failed count
- dry-run state
- filter scope
- upload configuration
- timestamps
- throttling counters
- worker utilization counters

Checkpoint snapshots do not include:

- raw email bodies
- attachment payloads
- raw SIS content
- adapter instances
- repository instances
- complete target documents
- full source archives

### Resume flow

```text
Load checkpoint
      ↓
Validate version and state
      ↓
Reconstruct continuation context
      ↓
Skip completed work
      ↓
Continue pipeline execution
```

The current checkpoint implementation is in-memory.

It demonstrates checkpoint and resume semantics but is not durable across process loss.

Production use would require a durable adapter backed by a database, key-value store, or other persistent system.

---

## 20. Verification and Reconciliation

### Verification

Verification occurs after successful target upload.

The verification step can compare:

- stable source identifier
- target identifier
- checksum
- essential metadata
- retention metadata where represented
- timestamps where compatible

Verification results remain deterministic and structurally represented.

Possible verification outcomes include:

- verified
- missing target document
- checksum mismatch
- metadata mismatch
- timestamp mismatch
- retention mismatch

One verification failure does not automatically invalidate successful results for unrelated items.

Dry-run skipped uploads are not treated as verification failures.

Idempotent replays are not treated as failures.

### Reconciliation

Reconciliation compares expected migration scope with observed target outcomes.

The reconciliation result may include:

- expected item count
- uploaded item count
- verified item count
- idempotent replay count
- dry-run item count
- missing identifiers
- unexpected identifiers
- checksum mismatches
- reconciliation status

Unsupported FSA items remain visible as unsupported outcomes or warnings. They are not silently treated as successful full-content migrations.

---

## 21. Reporting

Reporting is generated from immutable runtime contracts.

The reporting layer may include:

- `ExecutionReport`
- `ExecutionResult`
- `MigrationMetrics`
- `ProgressSnapshot`
- `ErrorBreakdownEntry`
- reconciliation results
- warnings
- execution status
- scope and filter information

The report layer is target-neutral and does not depend on mock storionX storage classes.

### JSON Export

JSON export provides:

- deterministic serialization
- stable field structure
- UTF-8-safe output
- execution metrics
- warnings
- reconciliation information
- structured errors
- target-neutral values

JSON output is suitable for:

- automated processing
- audit storage
- CI validation
- API responses
- operational tooling

The exporter serializes report data. It does not necessarily write a file unless an external caller performs file persistence.

### CSV Export

CSV export provides a flat, audit-oriented representation of structured error information.

Features include:

- deterministic headers
- deterministic row ordering
- one row per error entry
- spreadsheet-friendly formatting
- formula-injection protection
- no raw stack traces
- no payload content

Values beginning with spreadsheet formula prefixes such as the following are neutralized:

```text
=
+
-
@
```

CSV export is intentionally narrower than the complete JSON report.

### Structured Error Breakdown

A structured error entry may include:

- source identifier
- archive identifier
- migration stage
- error category
- error code
- message
- retryable status
- attempt count
- final status
- item type

Structured errors can originate from:

- transformation failures
- upload failures
- verification failures
- retry exhaustion
- idempotency conflicts
- pipeline-level failures

Raw exception stack traces and source payloads are excluded from structured exports.

---

## 22. Error Handling and Failure Isolation

The migration engine uses structured failure isolation.

One failed item does not necessarily stop the entire migration.

Examples:

- an unsupported FSA item does not stop supported mailbox content
- a failed mailbox item does not remove successful journal results
- an upload failure can be retried independently
- a verification mismatch remains visible without discarding other successful verifications
- reconciliation records partial outcomes
- filtered-out items remain non-errors
- dry-run skips remain non-errors
- idempotent replays remain non-errors

Terminal errors may include:

- unsupported item classification
- transformation failure
- retry exhaustion
- upload failure
- idempotency conflict
- missing target document
- checksum mismatch
- metadata mismatch
- invalid checkpoint
- invalid resume state

Not every error is retryable.

Failure classification determines whether the runner should:

- retry
- skip
- record a warning
- mark an item failed
- fail a pipeline stage
- terminate the migration

---

## 23. Security and Data Handling

The current repository applies security-oriented design principles through data minimization and boundary control.

### Current safeguards

- checkpoints do not store raw payloads
- reports do not store raw payloads
- structured exports do not include stack traces
- retry records contain minimal attempt metadata
- runtime contracts are immutable
- serialization remains target-neutral
- source mutation is excluded
- CSV formula prefixes are neutralized
- checksums and stable identifiers support auditability
- logs are not used as the authoritative reporting source

### Production security not implemented

The repository does not currently provide:

- live TLS transport
- production authentication
- production authorization
- OAuth or service-account integration
- external secrets management
- encryption-key management
- production network clients
- production API gateways
- production certificate rotation
- role-based access control

These concerns belong in future production adapters and deployment infrastructure.

---

## 24. Chain of Custody and Compliance

Chain of custody is preserved through stable identifiers, immutable contracts, checksums, and structured migration evidence.

Migration evidence may include:

- stable source identifier
- Enterprise Vault archive identifier
- original timestamps
- folder path
- source path
- checksum
- archive type
- item type
- mailbox identity
- original owner metadata
- orphan ownership state
- sender and recipient metadata
- journal metadata
- retention category
- retention policy
- legal-hold state
- legal-hold policy identifier
- execution timestamps
- checkpoint history
- retry history
- verification outcome
- reconciliation outcome
- final reports
- JSON exports
- CSV exports

Legal hold and retention are separate concepts:

- retention controls normal policy duration
- legal hold represents an independent compliance constraint

Legal hold is not implemented by assigning an extremely long retention period.

The current implementation does not:

- delete source content
- mutate source archives
- rewrite shortcuts
- remove shortcuts
- generate PST exports
- generate ZIP legal-export packages

Reports and checkpoints are audit metadata. They are not archives of source payload content.

---

## 25. Development Commands

Activate the virtual environment before running development commands:

```bash
source .venv/bin/activate
```

### Linting

```bash
ruff check .
```

### Formatting validation

```bash
black --check .
```

### Static type checking

```bash
mypy src tests
```

### Python compilation validation

```bash
python -m compileall src
```

### Full test suite

```bash
pytest -q
```

### Warnings-as-errors test run

```bash
pytest -W error
```

### Git whitespace validation

```bash
git diff --check
```

### Pre-commit hooks

When pre-commit is installed and configured:

```bash
pre-commit run --all-files
```

Use actual Makefile targets when present in the repository. Direct tool commands above remain the authoritative development checks.

---

## 26. Testing

The repository uses Pytest for automated validation.

### Unit Tests

Unit tests validate isolated behavior such as:

- value objects
- domain entities
- retry decisions
- retry strategies
- state transitions
- configuration contracts
- SIS rehydration
- transformation logic
- idempotency
- rate limiting
- report serialization
- CSV formula sanitization
- structured error mapping

Run:

```bash
pytest -q tests/unit
```

### Integration Tests

Integration tests validate cooperation between:

- application services
- migration engine
- ports
- adapters
- checkpoint repositories
- retry repositories
- mock source services
- mock target services

Run:

```bash
pytest -q tests/integration
```

### End-to-End Tests

End-to-end tests exercise complete migration scenarios such as:

- mailbox migration
- journal migration
- orphaned archive handling
- legal-hold preservation
- SIS rehydration
- target upload
- retry recovery
- idempotent replay
- verification
- reconciliation
- reporting
- checkpoint/resume
- dry-run behavior

Run:

```bash
pytest -q tests/e2e
```

### Full Test Suite

```bash
pytest -q
```

### Warnings as Errors

```bash
pytest -W error
```

The README intentionally does not publish a static passing test count because the test suite may grow over time.

---

## 27. Quality Gates

The repository uses the following quality gates:

| Quality gate | Purpose |
|---|---|
| Ruff | Detects linting issues and common Python defects |
| Black | Validates consistent Python formatting |
| MyPy | Validates static type correctness |
| Pytest | Validates functional behavior |
| Pytest warnings-as-errors | Prevents ignored warnings from becoming hidden regressions |
| `compileall` | Confirms Python source files compile |
| `git diff --check` | Detects whitespace and patch formatting problems |
| pre-commit | Runs configured checks before commits |

Recommended full validation:

```bash
ruff check .
black --check .
mypy src tests
python -m compileall src
pytest -q
pytest -W error
git diff --check
```

These checks are available locally. No continuous-integration workflow is claimed unless a workflow is present in the repository.

---

## 28. Example Outcomes

### Successful Upload

A source item with a new `source_identifier` is transformed and uploaded as one target document.

### Idempotent Replay

The same `source_identifier` and checksum return the existing target identifier without creating another document.

### Idempotency Conflict

The same `source_identifier` with a different checksum produces an explicit conflict and no duplicate target document.

### Throttled Upload

A deterministic 429-style target response provides retry-after information. The retry policy may delay and retry the operation.

### Temporary Service Failure

A deterministic 503-style failure exercises retry, backoff, recovery, and retry exhaustion behavior.

### Unsupported FSA

An FSA item remains visible as unsupported in warnings or structured reporting while supported mailbox and journal items continue.

### Orphaned Archive

The stable archive identifier and original owner metadata remain preserved. No fake active owner is created.

### Dry Run

The migration pipeline processes scope and produces reports without mutating target storage.

### Verification Failure

A missing target document or checksum mismatch appears as a structured verification result.

### Reconciliation Mismatch

Missing identifiers, unexpected identifiers, or checksum mismatches appear in the reconciliation output.

---

## 29. Known Limitations

The current repository does not implement:

- production Enterprise Vault SDK integration
- live Enterprise Vault SQL catalog integration
- live storionX REST API integration
- full FSA file-content migration
- SharePoint migration
- source-side shortcut deletion
- source-side shortcut rewriting
- PST legal-export generation
- ZIP legal-export generation
- durable target storage
- durable checkpoint persistence
- durable retry persistence
- distributed worker coordination
- cross-process work leasing
- a production full-text search index
- a production secrets manager
- a production observability backend
- production authentication
- production authorization
- real TLS-enabled network communication
- production deployment manifests
- a Kubernetes deployment
- an actual TB-to-PB execution benchmark
- production disaster-recovery behavior
- production capacity testing

The current source, target, checkpoint, retry, and report-support implementations are intended for deterministic development, architectural demonstration, and automated testing.

---

## 30. Future Improvements

Potential future extensions include:

- production Enterprise Vault SDK adapter
- production Enterprise Vault SQL catalog adapter
- production storionX REST adapter
- durable checkpoint repository
- durable retry repository
- database-backed audit storage
- durable target metadata storage
- streaming payload extraction
- bounded streaming transformation
- external object staging
- partitioning by vault store
- partitioning by archive
- partitioning by date range
- distributed workers
- lease-based partition ownership
- resumable distributed partitions
- target-aware adaptive throughput control
- partition-level reconciliation
- tenant and directory identity mapping
- manual exception mapping
- full FSA content migration
- SharePoint migration
- approved post-migration shortcut cleanup
- legal-export packaging
- production authentication and authorization
- TLS-enabled clients
- secrets management
- key management
- centralized metrics
- distributed tracing
- alerting
- operational dashboards
- deployment automation
- container orchestration
- TB-to-PB capacity testing

These are future capabilities and are not presented as implemented behavior.

---

## 31. Design Documentation

Detailed architecture and design information is available in [DESIGN.md](DESIGN.md).

The design document covers:

- Enterprise Vault domain concepts
- storionX target concepts
- mailbox migration flow
- journal migration flow
- orphaned archive flow
- departed-user and legal-hold flow
- identity mapping
- FSA behavior
- source shortcut policy
- Clean Architecture
- Hexagonal Architecture
- DDD-inspired boundaries
- component-level pipeline view
- ADR-001 through ADR-012
- SIS rehydration
- retry policy
- rate limiting
- 429 handling
- 503 handling
- parallel upload
- idempotency
- checkpoint and resume
- dry run
- filters
- verification
- reconciliation
- reporting
- JSON export
- CSV export
- structured errors
- security
- chain of custody
- retention and legal hold
- metadata preservation
- TB-to-PB scale considerations
- known limitations

---

## 32. Contributing

Create a focused branch:

```bash
git checkout -b feature/<name>
```

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run quality checks:

```bash
ruff check .
black --check .
mypy src tests
python -m compileall src
pytest -q
pytest -W error
git diff --check
```

Contributions should:

- preserve architectural boundaries
- keep the migration engine independent from infrastructure
- use ports for new external dependencies
- add tests for behavior changes
- keep runtime contracts immutable where appropriate
- update README and DESIGN documentation when behavior changes
- avoid storing raw payload content in checkpoints or reports
- keep validation checks passing
- avoid unrelated changes in the same commit

---

## 33. License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for the complete license text.

---

## 34. Acknowledgements

Veritas Enterprise Vault is the modeled source archive domain.

storionX is the modeled target archive domain.

This repository uses deterministic mock implementations for educational, architectural, development, and testing purposes. It does not claim to provide official Veritas Enterprise Vault or storionX integrations, and it does not claim official affiliation with those products or their owners.