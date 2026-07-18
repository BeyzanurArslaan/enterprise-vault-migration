# enterprise-vault-migration Design

## 1. Project Overview

`enterprise-vault-migration` is an enterprise migration engine for moving archived content from Veritas Enterprise Vault to storionX.

The repository implements a target-neutral orchestration platform rather than a CRUD application. Its responsibility is to coordinate discovery, extraction, SIS rehydration, transformation, upload, verification, reconciliation, checkpointing, retry handling, reporting, and export while keeping the migration engine isolated from concrete source and target implementations.

The implementation is intentionally layered:

- **Domain** defines immutable entities, identifiers, value objects, enums, and domain-level exceptions.
- **Application** coordinates commands, use cases, and services.
- **Migration Engine** owns the pipeline, step orchestration, runtime context, metrics, checkpointing, retry policy, reconciliation reporting, and export formatting.
- **Ports** define boundaries for source, target, checkpoint, retry, identity, clock, logging, and configuration concerns.
- **Adapters** connect the engine to in-memory development and test implementations.
- **Mock Enterprise Vault** and **mock storionX** provide deterministic test doubles for source and target behavior.

The codebase is designed for deterministic execution, strict typing, immutable contracts, and high testability.

### High-level structure

```text
Application
    ↓
Migration Engine
    ↓
Ports
    ↓
Adapters
    ↓
Mock Enterprise Vault / mock storionX
```

---

## 2. Assignment Scope

The repository is scoped to an end-to-end migration platform with a realistic orchestration layer and deterministic test fixtures.

Implemented scope includes:

- Enterprise Vault source modeling and mock source data generation.
- storionX target modeling and mock target storage.
- Migration pipeline execution with ordered steps.
- Dry run execution.
- Source filtering.
- SIS rehydration.
- Transformation to target-neutral documents.
- Upload, verification, reconciliation, and reporting.
- Checkpoint save and resume.
- Retry policy and retry execution.
- Structured JSON and CSV report export.
- Structured error breakdown reporting.

The project deliberately excludes real infrastructure concerns such as production databases, live REST clients, message brokers, and persistence engines.

---

## 3. Goals

The implementation is optimized for:

- **Correctness**: preserve source semantics, target metadata, checksums, retention, and provenance.
- **Determinism**: execute the same way for the same inputs and configuration.
- **Isolation**: keep the migration engine independent from mock source and target internals.
- **Immutability**: use frozen dataclasses for runtime contracts and reports.
- **Testability**: make every stage observable through unit, integration, and end-to-end tests.
- **Auditability**: capture structured progress, metrics, checkpoints, retries, and error breakdowns.
- **Compatibility**: preserve backward compatibility across application and engine layers.

---

## 4. Assumptions

The current implementation assumes:

- Enterprise Vault data is exposed through source-neutral contracts and mock source adapters.
- storionX is represented by a target port and in-memory mock target services.
- Execution is deterministic and single-process at the application boundary.
- Checkpoints are minimal continuation snapshots, not full payload archives.
- Retry decisions are deterministic and policy-driven.
- The assignment mentions random transient failures such as a 5% 503 rate, but the implementation deliberately uses deterministic, injectable transient failures instead of uncontrolled randomness so runs remain reproducible.
- All reports are derived from immutable runtime contracts.
- The repository is the source of truth for behavior; no external infrastructure is required for development or testing.

---

## 5. Enterprise Vault Overview

Enterprise Vault is treated as the source system of record. The repository models its migration-relevant concepts rather than its full product surface.

### Vault Store

The vault store represents the source repository holding archived content and metadata. In the codebase, vault store concepts are represented through source contracts, mock Enterprise Vault entities, and the discovery/extraction pipeline.

### Savesets

Savesets are the source-side containers that group archived content for extraction. The migration engine consumes them through source models and extraction results.

### SIS

Single Instance Storage is represented through SIS rehydration logic. The engine can reconstruct referenced content deterministically through the rehydration layer before transformation.

### Journal

Journal archives are represented as a distinct source scenario with metadata that must be preserved through transformation and target mapping.

### Mailbox Archives

Mailbox archives are modeled as the primary mail migration scenario. The pipeline preserves mailbox ownership, sender/recipient metadata, folder scope, retention, and timestamps.

### FSA

File System Archiving is explicitly represented in the source model and discovery flow. The current implementation preserves FSA archive identity and source-path metadata, but applies a deterministic unsupported-policy path instead of performing full file-content migration. Unsupported FSA archives remain visible in extraction warnings and structured reporting, and they do not stop unrelated mailbox or journal content from continuing through the pipeline.

### Shortcuts

Shortcuts are modeled as source-side references that may require special treatment during discovery and extraction. The engine preserves them structurally through source contracts and item classification.

### Metadata

Source metadata includes subject, sender, recipients, retention, item type, archive type, folder paths, original ownership, legal hold indicators, and custom properties. This metadata is preserved through the transformation layer and target adapter mapping.

### SQL Catalog

The SQL catalog is not implemented as a database in this repository. It is represented conceptually as the source metadata boundary that the mock Enterprise Vault layer exposes through deterministic contracts.

---

## 6. storionX Overview

storionX is the target platform represented by mock target services and a target port boundary.

### REST ingestion

The target adapter simulates REST-like ingestion semantics without exposing HTTP concepts to the migration engine. The engine interacts only with the target port.

### Metadata preservation

The target adapter maps transformed documents into mock storionX entities while preserving checksum, timestamps, sender/recipient metadata, retention information, legal hold indicators, and custom properties.

### Deduplication

Deduplication is modeled as idempotent upload behavior keyed by the stable `source_identifier`. Repeated uploads with the same checksum are treated as replays rather than duplicate document creation.

### Retention

Retention policy values are preserved through transformation and mapped into target metadata.

### Searchability

The mock target stores uploaded metadata in a form that supports deterministic lookup and verification by identifier and metadata fields. Full-text indexing and production search infrastructure are outside the current implementation.

---

## 7. Migration Scenarios

The repository supports the migration scenarios described in the assignment:

- **Mailbox**: user mailbox content with sender, recipient, folder, retention, and legal hold metadata.
- **Journal**: journaled mail flows with journal-specific compliance metadata.
- **Compliance**: content that must preserve retention, legal hold, and metadata traceability.
- **FSA**: file-system-like content with source paths and archive identity preserved, while full file-content migration remains unsupported.
- **Orphaned Archives**: content without a resolvable active owner, carried through source-neutral metadata.
- **Legal Hold**: content that preserves legal hold markers and related policy identifiers independently from retention duration.
- **Departed Users**: mailbox content owned by users who are no longer active, retained through owner resolution metadata.
- **Mixed Migration**: a combined execution containing multiple archive types and item types in one run.

Scenario handling is expressed through source contracts, transformation rules, target mapping, and report metadata rather than through a separate mapping pipeline step.

---

## 8. Identity Mapping

Identity mapping is a logical policy in the current design. It is expressed through source contracts, transformation rules, and target adapter mapping rather than through a dedicated mapping engine.

### Mailbox archives

- The source mailbox or owner identity determines the logical target archive.
- The mock mapping is deterministic.
- The original source archive identity remains retained in transformed metadata.

### Journal archives

- Mapping is archive- and compliance-store-based.
- It is not dependent on a normal mailbox owner.
- Journal metadata remains attached to the transformed document and target metadata.

### Orphaned archives

- No replacement owner is fabricated.
- Unresolved ownership is represented explicitly.
- A deterministic orphan policy is applied.

### FSA archives

- Source archive identity and source-path metadata are preserved.
- Full file-content migration is currently unsupported.
- Unsupported items remain visible rather than being silently discarded.

### Production future options

- Directory lookup
- Tenant mapping table
- External identity service
- Manual exception mapping

---

## 9. General Migration Pipeline

The migration flow is a deterministic pipeline coordinated by the runner.

```text
Discovery
    ↓
Mapping
    ↓
Extraction
    ↓
SIS Rehydration
    ↓
Transformation
    ↓
Upload
    ↓
Verification
    ↓
Reconciliation
    ↓
Reporting
```

### Step interpretation

- **Discovery** identifies archives and source scope.
- **Mapping** is expressed through source contracts and transformation rules rather than a separate orchestration step.
- **Extraction** turns source archives into item-level runtime results.
- **SIS Rehydration** reconstructs referenced content when required.
- **Transformation** produces target-neutral `TransformedDocument` objects.
- **Upload** maps transformed documents into mock storionX documents through the target port.
- **Verification** reads target documents back through the target port and compares stable identifiers, checksums, and essential metadata.
- **Reconciliation** summarizes the final source-to-target comparison in the report layer.
- **Reporting** consolidates execution summary, metrics, error breakdown, and export formats.

The pipeline runner advances through these stages in order, preserving immutable runtime context at each boundary.

---

## 10. Detailed Mailbox Migration Flow

1. Discover the mailbox archive and its archive metadata.
2. Resolve the logical storionX destination.
3. Apply archive, folder, and date filters.
4. Extract mail metadata, attachment references, and SIS part references.
5. Rehydrate SIS-backed content.
6. Use an execution-scoped SIS cache.
7. Validate part order, checksum, and size.
8. Transform into a target-neutral document.
9. Preserve subject, sender, recipients, folder, source timestamps, retention, legal hold, source identifiers, and checksum.
10. Upload using bounded parallel workers.
11. Respect rate limiting.
12. Retry deterministic 429/503-style transient failures.
13. Verify target identity, checksum, and essential metadata.
14. Reconcile expected and observed results.
15. Do not mutate or delete source shortcuts; refer to the source shortcut and cleanup policy for source-side handling.
16. Generate JSON, CSV, metrics, warnings, and structured error reporting.

---

## 11. Detailed Journal Migration Flow

1. Discover the journal archive independently from mailbox ownership.
2. Preserve the journal archive identity.
3. Preserve compliance context and journal metadata.
4. Extract sender, recipients, envelope-related metadata, timestamps, and SIS references.
5. Rehydrate body and attachment parts.
6. Transform while preserving compliance metadata.
7. Map to a logical storionX compliance store.
8. Upload with idempotency, throttling, retry, and failure isolation.
9. Verify checksum and compliance metadata.
10. Reconcile source and target outcomes.
11. Report unsupported or failed items without stopping other archives.

---

## 12. Detailed Orphaned Archive Flow

1. Discover the archive by stable EV archive identifier.
2. Attempt owner resolution.
3. Classify the archive as orphaned when no active owner exists.
4. Preserve original owner identity when available.
5. Do not fabricate a target user.
6. Preserve orphan state in source-neutral metadata.
7. Extract and rehydrate supported content.
8. Transform with orphan metadata.
9. Apply the deterministic orphan handling policy.
10. Upload supported content idempotently.
11. Verify and reconcile.
12. Report unresolved ownership clearly.

---

## 13. Departed User and Legal Export Flow

The repository models departed-user and legal-hold migrations as a compliance-preserving ingestion flow into storionX. It does not generate a PST, ZIP, or another physical legal-export package.

1. Discover the source archive by the stable Enterprise Vault archive identifier.
2. Preserve the original mailbox or owner metadata.
3. Preserve legal hold independently from retention duration.
4. Preserve the legal hold policy identifier where available.
5. Rehydrate SIS-backed content.
6. Preserve timestamps, folder path, source identity, checksum, retention, and provenance.
7. Upload idempotently.
8. Verify and reconcile.
9. Generate auditable reporting.

Legal hold is treated as compliance metadata, not as a synonym for a very long retention period.

---

## 14. Orphaned Archive Policy

An archive is orphaned when the source model reports that no active owner can be resolved for the archive, even though the original Enterprise Vault archive identifier is still known.

Policy:

- The archive remains discoverable.
- No fake active owner is invented.
- Original owner metadata is preserved when available.
- Unresolved ownership stays explicit in transformed metadata and reporting.
- Supported content can still proceed through the pipeline.
- Production routing could use quarantine, holding archive, manual mapping, or policy review.
- The current mock implementation applies deterministic handling so runs remain reproducible.

---

## 15. Source Shortcut and Cleanup Policy

Enterprise Vault shortcuts are source-side references. The migration uses archived content, not shortcut placeholder bytes.

Policy:

- Valid shortcut relationships remain represented in the mock source model.
- Stale or broken shortcuts may be reported.
- The current project does not delete, rewrite, restore, or clean up shortcuts.
- Source mutation is intentionally excluded.
- Destructive cleanup would require a separate approved post-migration process.
- Production cleanup should happen only after verification, reconciliation, business approval, and rollback planning.

---

## 16. Architecture

The repository follows Clean Architecture, Hexagonal Architecture, and DDD-inspired boundaries.

### Clean Architecture

Inner layers define contracts and policies. Outer layers provide implementation details. The migration engine depends on ports, not on concrete adapters.

### Hexagonal Architecture

Ports define the application-facing boundary. Adapters implement source, target, checkpoint, retry, and storage behaviors around that boundary.

### Domain-Driven Design

The domain layer contains the core language of the system: identifiers, archive types, item types, migration states, retry strategies, checkpoints, and domain errors.

### Ports & Adapters

The engine reads and writes through ports such as:

- `EnterpriseVaultSourcePort`
- `StorionXTargetPort`
- `CheckpointRepositoryPort`
- `RetryRepositoryPort`
- `IdentifierGeneratorPort`
- `ClockPort`
- `ConfigurationPort`
- `LoggerPort`

### Dependency Rule

Dependencies point inward:

- Application code depends on engine contracts.
- Engine code depends on domain and ports.
- Adapters depend on engine contracts and mock implementations.
- Domain code does not depend on application, engine, or adapters.

### Architectural diagram

```text
         ┌──────────────────────┐
         │     Application      │
         └─────────┬────────────┘
                   ↓
         ┌──────────────────────┐
         │   Migration Engine   │
         │  pipeline, steps,    │
         │  metrics, reports    │
         └─────────┬────────────┘
                   ↓
         ┌──────────────────────┐
         │        Ports         │
         └─────────┬────────────┘
                   ↓
         ┌──────────────────────┐
         │      Adapters        │
         └─────────┬────────────┘
                   ↓
     ┌──────────────┴──────────────┐
     │                             │
┌───────────────┐           ┌───────────────┐
│ mock EV source │           │ mock storionX │
└───────────────┘           └───────────────┘
```

### Component-Level Pipeline View

```text
                    +---------------------------+
                    |   Migration Orchestrator  |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    |      Pipeline Runner      |
                    +-------------+-------------+
                                  |
          +-----------------------+-----------------------+
          |                                               |
          v                                               v
 +--------------------+                         +--------------------+
 | Step Registry      |                         | Runtime Context    |
 | deterministic order|                         | metrics/checkpoint |
 +---------+----------+                         +---------+----------+
           |                                              |
           +----------------------+-----------------------+
                                  |
                                  v
                        +--------------------+
                        | Discover Step      |
                        +---------+----------+
                                  |
                                  v
                        +--------------------+
                        | Extract Step       |
                        +---------+----------+
                                  |
                                  v
                        +----------------------------+
                        | Transform Step             |
                        | includes SIS rehydration   |
                        +---------+------------------+
                                  |
                                  v
                        +--------------------+
                        | Upload Step        |
                        | bounded workers    |
                        +---------+----------+
                                  |
                                  v
                        +--------------------+
                        | Verify Step        |
                        +---------+----------+
                                  |
                                  v
                        +--------------------+
                        | Reconciliation     |
                        +---------+----------+
                                  |
                                  v
                        +--------------------+
                        | Final Reporting    |
                        | JSON / CSV export  |
                        +--------------------+
```

MigrationOrchestrator is the application-facing entry point. PipelineRunner coordinates execution. StepRegistry preserves deterministic step ordering. Runtime context carries immutable state, metrics, retries, and checkpoints. Source and target access still occurs through ports and adapters. SIS rehydration is integrated into the transformation flow and is not a separate deployment service. Reporting is produced from structured runtime results, not logs.

---

## 17. Component Responsibilities

### Domain

- `MigrationJob`, `Archive`, `MailItem`, `Attachment`, `ArchivedFile`, `Checkpoint`, `RetryRecord`
- identifiers and value objects such as `MigrationJobId`, `MigrationItemId`, `ArchiveId`, `Checksum`, and related types
- enums such as `ArchiveType`, `ItemType`, `JobStatus`, `MigrationStatus`, and `RetryStrategy`
- domain exceptions such as validation, checkpoint, idempotency, and resume errors

### Application

- `StartMigrationCommand`, `ResumeMigrationCommand`, `PauseMigrationCommand`, `CancelMigrationCommand`
- `MigrationOrchestrator`
- `MigrationService`, `CheckpointService`, `ReportingService`, `AssessmentService`
- `ResumeMigrationUseCase`

### Migration Engine foundation

- `MigrationConfiguration` for immutable orchestration settings
- `MigrationContext` and `ExecutionContext` for execution metadata
- `MigrationStepContext` for shared immutable step state
- `MigrationStateMachine` for legal state transitions
- `ProgressTracker` for runtime progress snapshots
- `MigrationMetrics` for aggregated counts and timing data
- `ExecutionReport` and `ExecutionResult` for final outcomes

### Pipeline runner and registry

- `StepRegistry` resolves step order deterministically.
- `PipelineRunner` coordinates step execution, state transitions, retries, checkpoints, and final reporting.

### Pipeline steps

- `DiscoverArchivesStep`
- `ExtractItemsStep`
- `TransformItemsStep`
- `UploadItemsStep`
- `VerifyItemsStep`
- `FinalizeMigrationStep`

Each step implements the `PipelineStep` contract and operates on immutable execution context objects.

### Source-side engine layers

- discovery results and extraction results provide stage-specific runtime data
- SIS rehydration reconstructs content when required
- transformation converts extracted content into target-neutral documents
- unsupported FSA archives are represented explicitly in extraction warnings and the final report

### Target-side engine layers

- `UploadBatchResult` captures upload orchestration metadata
- `VerificationResult` captures verification outcomes
- `ReconciliationResult` captures source-to-target comparison summaries

### Reporting

- `ExecutionReport` captures high-level run outcomes
- `ErrorBreakdownEntry` captures structured failure data
- JSON and CSV exporters serialize the final report deterministically

### Adapters

- `MockEnterpriseVaultSourceAdapter` supplies deterministic source data
- `MockStorionXTargetAdapter` maps transformed documents into mock storionX entities
- in-memory checkpoint and retry repositories support local execution and tests

---

## 18. SIS Rehydration

SIS rehydration is implemented as a deterministic orchestration layer that reconstructs SIS-backed content before transformation.

### Implemented behavior

- rehydration uses source contracts, not raw storage internals
- an execution-scoped cache prevents repeated work within the same run
- rehydrated content is summarized through `RehydratedContent`
- rehydration failures are tracked through metrics and reporting

### Boundary rules

- the engine does not expose raw SIS content in checkpoints or reports
- rehydration does not mutate the source system
- rehydration is part of the pipeline, not a separate persistence subsystem

---

## 19. Retry Strategy

Retry is policy-driven and deterministic.

### Implemented retry model

- `RetryStrategy` defines the retry shape.
- `RetryDecision` is the immutable decision output.
- `RetryPolicy` computes whether another attempt is allowed and what delay should be used.
- `RetryRecord` captures attempt history when a retry repository is configured.
- `RetryRepositoryPort` defines the persistence boundary for retry records.

### Attempt numbering

- Attempt `1` is the initial execution.
- `max_attempts` includes the initial execution.
- `remaining_attempts` counts how many additional attempts are still available after the current attempt.

### Strategy behavior

- `NONE`: no retries.
- `FIXED_DELAY`: deterministic constant delay.
- `EXPONENTIAL_BACKOFF`: deterministic exponential delay capped by the configured maximum and without jitter.

### Runner integration

The pipeline runner evaluates retryability for unexpected failures, persists retry records when configured, updates retry metrics, and sleeps through an injected callable instead of calling `time.sleep()` directly.

Item-level upload or verification mismatches are represented structurally and do not trigger whole-step retry by themselves.

---

## 20. Rate Limiting

Rate limiting is implemented in the mock storionX target layer, not in the migration engine.

`UploadRateLimiter` is:

- execution-scoped
- thread-safe
- deterministic
- configurable in requests per second
- free of global mutable state

The limiter returns a retry-after delay rather than sleeping. This allows the target adapter to emulate capacity pressure while leaving retry orchestration to the engine.

---

## 21. 429 Handling

The mock storionX target adapter can raise a `TooManyRequestsError` when the shared rate limiter indicates that an upload should be deferred.

Behavior:

- retry-after semantics are preserved as a numeric delay
- the migration engine remains unaware of HTTP types
- retry policy and retry classifier determine whether the attempt is retried
- no duplicate target documents are created during a throttled attempt

This keeps 429 handling inside the adapter boundary while still exercising the retry subsystem realistically.

---

## 22. 503 Handling

The mock storionX target adapter can simulate temporary service outages through `ServiceUnavailableError`.

Behavior:

- temporary failures are deterministic and injectable
- the retry layer can recover when the failure is classified as retryable
- permanent failures still propagate as failures
- transport semantics remain hidden from the migration engine

The assignment suggests random transient failures such as a 5% 503 rate. The implementation deliberately uses deterministic, injectable transient failures instead of uncontrolled randomness so the retry, backoff, recovery, and failure-isolation behavior stays reproducible.

---

## 23. Parallel Upload

Parallel upload is bounded and deterministic.

### Implemented behavior

- The upload step uses a configurable worker count.
- The shared rate limiter is safe to use from concurrent workers.
- The target adapter remains authoritative for idempotency.
- Duplicate source identifiers are suppressed before upload fan-out.
- Reported item ordering remains deterministic.

### Scheduling diagram

```text
Transformed documents
        ↓
  de-duplicate by
  source_identifier
        ↓
 bounded worker pool
        ↓
 target adapter
        ↓
 ordered results
```

The engine does not expose worker coordination to the domain model. Concurrency is an orchestration concern only.

---

## 24. Idempotency

Idempotency is implemented at the target adapter boundary.

### Stable key

The stable idempotency key is the transformed document’s `source_identifier`.

### Behavior

- first upload creates one target document
- replay with the same checksum returns the same target identifier
- replay is recorded as an idempotent replay
- conflicting checksum replays raise `IdempotencyConflictError`
- no duplicate target record is created for the same key

Idempotency remains authoritative in the target adapter, which is the correct boundary for duplicate prevention.

---

## 25. Checkpoint / Resume

Checkpointing and resumption are implemented through minimal immutable snapshots.

### Components

- `CheckpointSnapshot` stores continuation data only.
- `CheckpointRepositoryPort` defines persistence behavior.
- `CheckpointService` coordinates repository access.
- `InMemoryCheckpointRepository` provides a development and test implementation.
- `ResumeMigrationUseCase` loads and validates checkpoints before re-entering the pipeline.

### Snapshot contents

The checkpoint stores only the minimal state needed to continue orchestration:

- migration job identifier
- completed step name
- last processed item identifier
- counts for processed, successful, failed, skipped, uploaded, and verification-failed items
- current state
- timestamps
- filter scope
- dry-run flag and counts
- upload worker and rate-limit settings
- throttling and worker utilization counters

It does **not** store raw email bodies, attachment payloads, adapters, repositories, or full target documents.

### Resume flow

```text
Loaded checkpoint
      ↓
validate version and state
      ↓
reconstruct step context
      ↓
resume from next step
      ↓
continue normal checkpoint saving
```

Resume skips already completed steps and preserves the latest valid checkpoint and execution metrics.

---

## 26. Dry Run

Dry run is an implemented configuration mode that exercises the migration pipeline without mutating the target system.

Behavior:

- target upload is skipped
- dry-run item counters are tracked
- the report can resolve to a dry-run-specific final status
- checkpoint and resume remain structurally compatible
- verification and reconciliation logic can still operate on deterministic runtime state

Dry run is a first-class orchestration mode, not a separate engine.

---

## 27. Filters

The migration configuration supports source-scope filtering through immutable fields:

- archive names
- folder paths
- start date
- end date

Filters are preserved through execution context, reports, and checkpoints so that the run can be audited and resumed consistently.

Filtering is a source-side concern. The target adapter does not interpret migration filters.

---

## 28. Verification

Verification is implemented as a post-upload comparison step that uses the target port boundary.

### Implemented behavior

- verify only documents that were successfully uploaded
- compare stable identifiers
- compare checksums
- compare essential metadata
- compare retention where represented
- compare timestamps where compatible
- preserve deterministic ordering
- record missing, checksum-mismatched, and metadata-mismatched identifiers structurally

### Failure isolation

- one failed item does not terminate the full migration
- successful verification results are preserved even when another item fails
- dry-run skipped uploads are not treated as verification failures
- idempotent replays are not treated as failures

---

## 29. Reconciliation

Reconciliation is represented as a structured result model rather than as a persistence-heavy subsystem.

`ReconciliationResult` compares the transformed source scope against the observed target outcome using stable identifiers and checksum metadata.

The final report can carry:

- expected item counts
- uploaded item counts
- verified item counts
- idempotent replay counts
- dry-run counts
- missing identifiers
- unexpected identifiers
- checksum mismatches
- reconciliation status

The implementation remains target-neutral and does not require full target re-scanning beyond the available safe lookup boundary.

Unsupported FSA items and other structural warnings remain visible in reports; they do not masquerade as silent success.

---

## 30. Reporting

Reporting is implemented as a deterministic, immutable summary of the migration run.

### Implemented report contracts

- `ExecutionReport`
- `ExecutionResult`
- `MigrationMetrics`
- `ProgressSnapshot`
- `ErrorBreakdownEntry`

### Report responsibilities

- summarize final run status
- preserve scope and filter metadata
- surface counts, warnings, and timing
- carry metrics and reconciliation information
- expose structured error breakdowns
- support stable JSON and CSV exports

The report layer is intentionally pure so it can be reused by CLI, tests, APIs, and file export logic.

---

## 31. JSON Export

JSON export is provided by the reporting package through deterministic serialization helpers.

Behavior:

- uses the canonical report dictionary serializer
- preserves stable key ordering
- emits UTF-8-safe JSON text
- avoids infrastructure-specific objects
- includes error breakdown entries and structured metrics

The JSON export is suitable for automation, CI consumption, and structured audit artifacts.

---

## 32. CSV Export

CSV export is provided as a flat audit table derived from the structured error breakdown.

Behavior:

- deterministic header and row ordering
- one row per error breakdown entry
- spreadsheet formula sanitization for leading `=`, `+`, `-`, and `@`
- no HTTP or infrastructure-specific fields
- safe for spreadsheets and basic audit tooling

CSV export is intentionally narrow and audit-oriented rather than a full report dump.

---

## 33. Structured Error Breakdown

Structured error breakdowns represent terminal failures in a target-neutral way.

### Model

`ErrorBreakdownEntry` captures:

- source identifier
- stage
- category
- code
- message
- retryability
- attempt count
- final status
- archive identifier
- item type

### Sources of entries

- transformation failures
- upload failures
- verification failures
- pipeline-level failures when no item-level source is available

### Properties

- deterministic
- serializable
- security-safe
- suitable for JSON and CSV export

The breakdown exists to explain failures without exposing raw exceptions or payload content.

---

## 34. Security

Security is implemented through data minimization and strict boundary control.

### Data minimization

- checkpoints store only continuation data
- reports store only structured metadata and error summaries
- retry records store minimal attempt data
- exports avoid raw payloads and stack traces

### Boundary rules

- the migration engine does not import mock storionX internals
- the migration engine does not store adapter or repository instances in runtime contracts
- serialization remains target-neutral

### CSV safety

Spreadsheet formula prefixes are neutralized during CSV export to prevent accidental formula execution.

---

## 35. Chain of Custody

The repository preserves chain of custody through immutable contracts and stable identifiers.

Evidence is carried through the system as:

- stable source identifiers
- original archive identifiers
- original timestamps
- folder or source path
- checksum
- retention category and policy
- legal hold state
- archive type
- item type
- orphan ownership state
- journal metadata
- execution timestamps
- checkpoint history
- retry history where configured
- verification outcome
- reconciliation outcome
- final report and exports

Raw content is not stored in checkpoints or reports. Those artifacts are audit metadata, not source payload archives. Source mutation is excluded from the current flow.

---

## 36. Retention and Legal Hold Preservation

Retention and legal hold are preserved as distinct compliance concepts.

### Source to target flow

- source retention metadata is extracted from Enterprise Vault models
- transformation carries retention policy into `TransformedDocument`
- the target adapter maps retention into mock storionX metadata
- verification checks that the target document still matches the transformed contract

### Legal hold clarity

- legal hold is independent from normal retention duration
- legal hold flags are preserved
- legal hold policy identifiers are preserved where available
- legal hold is part of compliance metadata
- legal hold survives transformation and target mapping
- legal hold items are not silently excluded
- legal hold does not mean “use a very long retention period”

Retention is treated as the policy duration, while legal hold is treated as a separate compliance constraint.

---

## 37. Metadata Preservation

The repository preserves a broad set of migration metadata:

- subject
- sender and recipient lists
- CC and BCC recipients
- archive type
- item type
- mailbox address
- folder path
- source path
- ownership and owner-resolution metadata
- legal hold information
- journal metadata
- custom properties
- checksum
- timestamps
- attachment metadata

The target adapter maps this metadata into mock storionX entities, and verification compares essential metadata back through the target port.

---

## 38. Scalability

The repository is designed to scale by changing adapters and runtime configuration rather than changing the core engine.

### Current implementation

- in-memory simulation
- bounded worker upload
- shared limiter
- deterministic retry
- checkpoint/resume
- immutable contracts
- target-neutral ports

### TB–PB Scale Considerations

The architecture can evolve toward larger migration volumes by introducing:

- partitioning by vault store, archive, time range, or source partition
- durable checkpoint storage
- durable retry records
- streaming extraction
- bounded memory
- bounded queues and backpressure
- distributed workers
- lease-based work ownership
- resumable partitions
- target-aware throughput control
- external temporary content staging
- archive-level and partition-level reconciliation
- operational dashboards
- alerting
- metrics and tracing
- failure isolation
- idempotent distributed execution

### Future production scale

These large-scale capabilities belong to durable and distributed infrastructure. The current repository does not claim PB-scale production execution, but the architecture is prepared for that evolution.

---

## 39. Architectural Decisions

### ADR-001 — Clean Architecture

**Decision**

Keep migration policy and orchestration independent from infrastructure implementations.

**Rationale**

The migration engine must remain stable while source, target, persistence, logging, and configuration implementations evolve. Dependencies therefore point toward domain policies and abstract ports.

**Consequence**

Mock and production adapters can evolve independently from the engine. This separation requires disciplined contracts and explicit dependency boundaries.

### ADR-002 — Hexagonal Architecture

**Decision**

Use ports and adapters for source, target, checkpoint, retry, clock, logging, identity, checksum, and configuration boundaries.

**Rationale**

The current in-memory implementations must be replaceable by production services without changing migration orchestration.

**Consequence**

Infrastructure details remain isolated. Every adapter must honor stable port semantics and target-neutral contracts.

### ADR-003 — Centralized Retry Orchestration

**Decision**

Keep retry policy evaluation and retry execution centralized in the pipeline runner.

**Rationale**

Centralized retry handling avoids duplicated retry loops across pipeline steps and adapters. Adapters may expose retryable failures and retry-after metadata, but they do not own migration-level retry orchestration.

**Consequence**

Retry behavior remains deterministic, observable, and testable. The runner must consistently classify failures and preserve retry records and metrics.

### ADR-004 — Target-Neutral Contracts

**Decision**

Use source-neutral and target-neutral immutable contracts between architectural layers.

**Rationale**

Mock Enterprise Vault entities and mock storionX entities must not leak into migration-engine policies.

**Consequence**

Production adapters can replace mock implementations without rewriting the pipeline. Translation logic remains the responsibility of adapters and transformation boundaries.

### ADR-005 — Execution-Scoped SIS Cache

**Decision**

Scope the SIS rehydration cache to one migration execution.

**Rationale**

The cache prevents repeated SIS part reads during one run while avoiding global mutable state and cross-execution contamination.

**Consequence**

Rehydration remains deterministic and concurrency-safe. Cached content is not reused across independent migration executions.

### ADR-006 — Immutable Runtime Contracts

**Decision**

Use frozen dataclasses and immutable result models for runtime context, retry decisions, checkpoints, metrics, reports, and pipeline results.

**Rationale**

Immutable contracts improve determinism, testability, concurrency safety, and reasoning about pipeline state.

**Consequence**

State changes require explicit replacement or reconstruction instead of in-place mutation.

### ADR-007 — Minimal Checkpoint Snapshots

**Decision**

Persist only continuation state, scope, counters, timestamps, and audit metadata in checkpoints.

**Rationale**

Resume support does not require storing raw email bodies, attachments, SIS payloads, adapters, repositories, or target documents.

**Consequence**

Checkpoint artifacts minimize sensitive-data exposure and serialization complexity. Source content must remain available when a migration is resumed.

### ADR-008 — Deterministic Failure Simulation

**Decision**

Use injectable deterministic 429- and 503-style failures instead of uncontrolled random failures.

**Rationale**

Deterministic failures exercise retry, backoff, recovery, and failure isolation while keeping tests and demonstrations reproducible.

**Consequence**

The mock does not reproduce statistically random production traffic, but all failure scenarios can be tested reliably.

### ADR-009 — Rate Limiter at the Target Boundary

**Decision**

Keep target capacity and throttling simulation inside the mock storionX adapter boundary.

**Rationale**

Rate limits are target-service behavior. The migration engine must not depend on HTTP status codes or target transport implementation details.

**Consequence**

The engine observes neutral retry information such as retry-after duration while remaining target-neutral.

### ADR-010 — Bounded Parallel Upload

**Decision**

Use a configurable bounded worker pool with deterministic result ordering.

**Rationale**

Bounded concurrency improves throughput while preserving rate limiting, idempotency, reporting order, checkpoint consistency, and predictable resource usage.

**Consequence**

The implementation supports single-process concurrency. Distributed worker coordination and leasing remain future production concerns.

### ADR-011 — Idempotency at the Target Boundary

**Decision**

Use `source_identifier` as the stable idempotency key and enforce replay and conflict behavior in the target adapter.

**Rationale**

The destination boundary is authoritative for determining whether a source item has already been ingested.

**Consequence**

Same-checksum replays return the existing target identity safely. Conflicting checksum replays fail explicitly without creating duplicate records.

### ADR-012 — Reporting from Structured Results

**Decision**

Generate reports and exports from immutable pipeline result contracts rather than by parsing log output.

**Rationale**

Structured results produce deterministic, machine-readable, auditable, and testable reporting.

**Consequence**

Every terminal failure path must preserve sufficient structured metadata for reporting without leaking raw payloads or stack traces.

---

## 40. Future Improvements

Future improvements may include:

- durable checkpoint and retry storage
- production-grade logging sinks
- richer observability and trace propagation
- live source and target adapters
- externalized metrics collection
- additional export formats
- broader reconciliation across larger scopes
- stronger operational automation around execution artifacts

These items are intentionally future work and are not described as implemented behavior.

---

## 41. Known Limitations

The current repository does not implement:

- a production Enterprise Vault SDK integration
- a live Enterprise Vault SQL catalog integration
- a live storionX REST API client
- full FSA file-content migration; FSA uses a deterministic unsupported-policy path instead
- SharePoint migration
- source-side shortcut deletion or cleanup
- PST, ZIP, or another legal-export package generator
- a durable database-backed checkpoint repository
- a durable retry repository
- distributed worker coordination
- a production full-text search index
- an external secrets manager integration
- a production observability backend
- durable persistence for mock target and repository state
- real network, TLS, authentication, or authorization layers
- a production deployment manifest
- an actual TB–PB execution benchmark

These are true limitations of the repository today and should remain explicit until they are implemented.

---

## 42. Conclusion

`enterprise-vault-migration` implements a deterministic, layered migration engine for Enterprise Vault to storionX migrations.

The repository’s current design emphasizes:

- clean separation of concerns
- immutability and strict typing
- deterministic orchestration
- realistic adapter behavior
- auditable reporting
- safe checkpoint and retry handling
- source- and target-neutral contracts
- explicit handling for unsupported FSA content, orphaned archives, legal hold, shortcuts, and compliance-preserving flow

This foundation is ready for continued evolution without destabilizing the core migration engine. Although the repository uses mock Enterprise Vault and mock storionX implementations, the orchestration layer, architectural boundaries, retry model, checkpoint mechanism, reporting, idempotency, and transformation pipeline are intentionally designed so that production adapters can replace the current mock implementations without changing the migration engine itself.
