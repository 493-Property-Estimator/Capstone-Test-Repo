# Feature Specification: Schedule open-data refresh jobs

**Feature Branch**: `022-schedule-refresh-jobs`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-22.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-22-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-22-AT.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run scheduled refreshes safely (Priority: P1)

As a maintainer, I need the system to run open-data refresh workflows on schedule, in dependency order, with QA gates and safe publication so production data stays current without risking corruption.

**Why this priority**: This is the core operational outcome of the use case and the main source of business value.

**Independent Test**: Can be fully tested by triggering a scheduled refresh and confirming ordered execution, QA-gated promotion, version recording, and a success summary.

**Acceptance Scenarios**:

1. **Given** refresh schedules and dependencies are configured, **When** the scheduled time occurs, **Then** the scheduler triggers the workflow, records a workflow run ID, and marks the run as active in monitoring.
2. **Given** a workflow run starts, **When** steps execute, **Then** they run non-interactively in dependency order and record per-step identifiers and dataset version metadata for promoted datasets.
3. **Given** a dataset passes QA, **When** promotion occurs, **Then** the dataset is promoted atomically and updated production data becomes available for valuation.

---

### User Story 2 - Preserve production on failures (Priority: P2)

As a maintainer, I need failures to block unsafe publication, preserve last known-good production data, and report actionable diagnostics so I can respond without user-facing data corruption.

**Why this priority**: Protecting production data is required even when refreshes fail or partially succeed.

**Independent Test**: Can be fully tested by simulating QA failures, upstream dependency failures, start failures, missing secrets, time-window overruns, and promotion failures.

**Acceptance Scenarios**:

1. **Given** a dataset fails QA, **When** promotion is evaluated, **Then** promotion is blocked, production stays on the last known-good version, and the failure appears in the final summary and alerts.
2. **Given** a required upstream dataset fails, **When** dependent steps are evaluated, **Then** those steps are skipped or degraded according to policy and the dependency chain is recorded.
3. **Given** the workflow cannot start or cannot promote safely, **When** the failure occurs, **Then** no unsafe production change is made and an actionable alert is emitted.

---

### User Story 3 - Understand run outcomes clearly (Priority: P3)

As a maintainer, I need every scheduled or on-demand refresh run to produce a clear summary, logs, metrics, and traceable version records so I can audit what changed and why.

**Why this priority**: Operational clarity is necessary for trust, debugging, and downstream traceability.

**Independent Test**: Can be fully tested by completing scheduled and on-demand runs in success, partial-success, and retry conditions and verifying summaries, metrics, alerts, and identifiers.

**Acceptance Scenarios**:

1. **Given** a run completes with mixed outcomes, **When** the final summary is generated, **Then** it lists promoted, skipped, and failed datasets with reasons and reflects partial success accurately.
2. **Given** a transient failure occurs, **When** retry policy is applied, **Then** retry attempts and timing are recorded and the final run summary reflects the warning if the step later succeeds.
3. **Given** Sky triggers an on-demand refresh, **When** the workflow runs, **Then** it follows the same dependency ordering, QA gates, promotion behavior, and observability requirements as a scheduled run.

### Edge Cases

- Job start fails because of scheduler misconfiguration or missing permissions.
- A downstream job depends on an upstream dataset that failed ingestion.
- QA checks fail for a dataset during refresh.
- A refresh run exceeds its configured time window or resource limits.
- A required secret is missing or expired when the workflow starts.
- Promotion fails for one dataset after staging and QA complete.
- Some datasets are not due while others succeed or fail in the same run.
- A transient failure succeeds only after one or more retries.

## Requirements *(mandatory)*

### Summary / Goal

Enable the maintainer to schedule and run automated open-data refresh workflows so datasets and indicators remain current, production data stays safe, and each run is observable and traceable.

### Actors

- **Primary Actor**: Maintainer (System Operator)
- **Secondary Actors**: Scheduler/Orchestrator, Ingestion Pipeline, Database/Feature Store, Monitoring/Alerting, Open Data Providers

### Preconditions

- Ingestion use cases (UC-17/UC-18/UC-19) are implemented and runnable in an automated mode (non-interactive).
- A scheduler/orchestrator is available and has permissions to trigger jobs and access required secrets.
- Monitoring and alerting channels are configured (logs, metrics, notifications).
- Safe deployment strategy exists (staging + atomic promotion) so refreshes do not corrupt production data.

### Triggers

- The maintainer configures refresh schedules.
- The scheduler triggers a refresh run at the configured time.

### Main Flow

1. The maintainer defines refresh policies for each dataset type (e.g., geospatial weekly, POIs monthly, assessment annually, census annually).
2. The maintainer configures the scheduler with job definitions, dependencies, and time windows.
3. At the scheduled time, the scheduler triggers a refresh workflow.
4. The system runs ingestion steps in the configured order (e.g., geospatial + POIs, then census indicators, then assessment baselines) and writes results to staging.
5. The system runs QA checks and validates that each dataset meets promotion criteria.
6. The system promotes successful datasets to production tables atomically and records versions.
7. The system emits run metrics (duration, counts, warnings) and logs correlation IDs for traceability.
8. The system notifies the maintainer of success (dashboard/notification) and makes updated data available to the valuation engine.

### Alternate Flows

- **6a**: Partial refresh succeeds (some datasets updated, others not)
  - **6a1**: The system publishes updated datasets that passed QA and clearly reports which datasets are still on older versions.

### Exception / Error Flows

- **3a**: Job start fails (scheduler misconfiguration, missing permissions)
  - **3a1**: The scheduler reports the failure; the system alerts the maintainer with the failing job and reason.
- **4a**: A downstream job depends on an upstream dataset that failed ingestion
  - **4a1**: The system skips or degrades dependent steps (e.g., compute indicators using prior boundaries) based on policy.
  - **4a2**: The system alerts the maintainer and records the dependency failure chain.
- **5a**: QA checks fail during refresh
  - **5a1**: The system blocks promotion for the failing dataset and retains last known-good production data.
  - **5a2**: The system keeps staging outputs for debugging and alerts the maintainer.
- **7a**: Refresh run exceeds time window or resource limits
  - **7a1**: The system throttles, pauses, or aborts per configuration and alerts the maintainer.

### Data Involved

- Refresh policies for each dataset type
- Scheduler job definitions
- Job dependencies
- Time windows
- Staging outputs
- QA results and promotion criteria results
- Production dataset versions
- Run metrics, including duration, counts, and warnings
- Correlation IDs
- Notification content for success and failure outcomes

### Functional Requirements

- **FR-01-001**: The system MUST allow the maintainer to define refresh policies for each dataset type.
- **FR-01-002**: The system MUST allow the maintainer to configure scheduler job definitions, dependencies, and time windows for refresh workflows.
- **FR-01-003**: The system MUST trigger a refresh workflow at the configured scheduled time and record a workflow run ID and start timestamp.
- **FR-01-004**: The system MUST make active workflow runs visible in logs or monitoring with a running status.
- **FR-01-005**: The system MUST execute ingestion steps in the configured dependency order.
- **FR-01-006**: The system MUST run each ingestion step in automated, non-interactive mode.
- **FR-01-007**: The system MUST write ingestion outputs to staging before promotion.
- **FR-01-008**: The system MUST run QA checks for each dataset and validate promotion criteria before promotion.
- **FR-01-009**: The system MUST promote successful datasets to production atomically.
- **FR-01-010**: The system MUST record a per-step run identifier for each executed step.
- **FR-01-011**: The system MUST record dataset version or provenance metadata for each dataset promoted to production.
- **FR-01-012**: The system MUST emit run metrics including duration, counts, warnings, per-step status, and retry information.
- **FR-01-013**: The system MUST log correlation identifiers so workflow runs and step runs are traceable.
- **FR-01-014**: The system MUST notify the maintainer when a refresh run succeeds and make updated production data available to the valuation engine after promotion.
- **FR-01-015**: The system MUST emit an alert with the failing job or workflow and reason when a scheduled refresh cannot start.
- **FR-01-016**: The system MUST prevent ingestion steps from running when the workflow fails to start.
- **FR-01-017**: The system MUST keep production data unchanged for datasets that are not successfully promoted.
- **FR-01-018**: The system MUST skip or degrade dependent steps according to policy when an upstream dataset fails ingestion.
- **FR-01-019**: The system MUST record the dependency failure chain when dependent steps are skipped or degraded.
- **FR-01-020**: The system MUST block promotion for any dataset that fails QA.
- **FR-01-021**: The system MUST retain the last known-good production version for any dataset whose QA or promotion fails.
- **FR-01-022**: The system MUST retain staging outputs for debugging when QA fails.
- **FR-01-023**: The system MUST support partial refresh outcomes by publishing only datasets that passed QA and clearly reporting datasets that remain on older versions.
- **FR-01-024**: The system MUST throttle, pause, or abort a refresh run according to configuration when a step exceeds its time window or resource limits.
- **FR-01-025**: The system MUST emit an alert identifying the step and limit exceeded when time-window or resource-limit enforcement occurs.
- **FR-01-026**: The system MUST fail early with an actionable error when a required secret is missing or expired.
- **FR-01-027**: The system MUST prevent dataset promotion when a required secret is missing or expired.
- **FR-01-028**: The system MUST record actionable error details when promotion fails for a dataset.
- **FR-01-029**: The system MUST preserve the last known-good production version for a dataset whose promotion fails.
- **FR-01-030**: The system MUST produce a final workflow summary that lists datasets promoted with their new versions, datasets skipped with reasons, and datasets failed with reasons.
- **FR-01-031**: The system MUST represent mixed-outcome runs as partial success rather than full success.
- **FR-01-032**: The system MUST apply configured retry and backoff behavior to transient step failures and record retry attempts and timing.
- **FR-01-033**: The system MUST include retry warnings in the final run summary when a retried step eventually succeeds.
- **FR-01-034**: The system MUST support on-demand refresh runs that use the same dependency ordering, QA gates, promotion semantics, identifiers, metrics, and final summary as scheduled runs.

### Non-Functional Requirements

- **NFR-001**: Refresh outcomes MUST preserve last known-good production data whenever a run does not complete safe promotion for a dataset.
- **NFR-002**: Logs and metrics MUST provide enough operational detail to identify workflow runs, step outcomes, durations, counts, warnings, and errors.
- **NFR-003**: Alerts MUST provide actionable diagnostics for start failures, ingestion failures, QA failures, promotion failures, missing secrets, and time-window overruns.

### Key Entities *(include if feature involves data)*

- **Refresh Policy**: Defines dataset cadence and when a dataset type should be refreshed.
- **Workflow Run**: A scheduled or on-demand refresh execution identified by a workflow run ID and timestamps.
- **Step Run**: An individual ingestion step execution with its own identifier, status, retries, and metrics.
- **Dataset Version Record**: Traceability record for a promoted dataset, including version or provenance information.
- **Workflow Summary**: Final report of promoted, skipped, and failed datasets and their reasons.

### Assumptions

- This specification is limited to UC-22 flows and UC-22 acceptance-test checks.
- Scenario narrative content was used only to confirm terminology, not to create new behavior beyond the use case and acceptance tests.
- Implementation constraints for this repository remain Python and vanilla HTML/CSS/JS.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of scheduled refresh runs start at the configured time or emit a start-failure alert with no ingestion steps run.
- **SC-002**: In acceptance testing, 100% of datasets that fail QA, fail promotion, or are blocked by missing secrets remain on their last known-good production versions.
- **SC-003**: In acceptance testing, 100% of completed workflow runs produce a summary that identifies promoted datasets, skipped datasets, failed datasets, and the reason for each non-promoted outcome.
- **SC-004**: In acceptance testing, 100% of scheduled and on-demand runs record workflow identifiers, step-level identifiers, and sufficient logs or metrics to trace the outcome of each executed step.

## Traceability

### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-22-01 | FR-01-003, FR-01-004 |
| AT-22-02 | FR-01-005, FR-01-018, FR-01-019 |
| AT-22-03 | FR-01-006, FR-01-010, FR-01-011 |
| AT-22-04 | FR-01-020, FR-01-021, FR-01-030 |
| AT-22-05 | FR-01-018, FR-01-019, FR-01-017 |
| AT-22-06 | FR-01-023, FR-01-030, FR-01-031 |
| AT-22-07 | FR-01-012, FR-01-032, FR-01-033 |
| AT-22-08 | FR-01-024, FR-01-025, FR-01-017 |
| AT-22-09 | FR-01-015, FR-01-016, FR-01-017 |
| AT-22-10 | FR-01-026, FR-01-027, FR-01-017 |
| AT-22-11 | FR-01-028, FR-01-029, FR-01-030 |
| AT-22-12 | FR-01-034, FR-01-010, FR-01-012, FR-01-030 |

### Flow Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow 1 | FR-01-001 |
| Main Flow 2 | FR-01-002 |
| Main Flow 3 | FR-01-003, FR-01-004 |
| Main Flow 4 | FR-01-005, FR-01-006, FR-01-007 |
| Main Flow 5 | FR-01-008 |
| Main Flow 6 | FR-01-009, FR-01-011 |
| Main Flow 7 | FR-01-012, FR-01-013 |
| Main Flow 8 | FR-01-014 |
| Alternate Flow 6a | FR-01-023, FR-01-030, FR-01-031 |
| Exception Flow 3a | FR-01-015, FR-01-016, FR-01-017 |
| Exception Flow 4a | FR-01-018, FR-01-019, FR-01-017 |
| Exception Flow 5a | FR-01-020, FR-01-021, FR-01-022 |
| Exception Flow 7a | FR-01-024, FR-01-025, FR-01-017 |
