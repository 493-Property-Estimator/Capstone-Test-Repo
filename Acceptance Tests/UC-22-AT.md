# Acceptance Tests — UC-22: Schedule open-data refresh jobs

## Purpose
Verify that the system schedules and runs automated refresh workflows for open-data sources, executes ingestion steps in the correct dependency order, gates publication on QA, preserves last known-good production data on failures, and emits structured logs/metrics/alerts. Verify partial-success reporting, time-window enforcement, retries, and on-demand runs.

## References
* User Story: **US-22: Schedule open-data refresh jobs**
* Use Case: `Use Cases/UC-22.md`
* Scenario: `Scenarios/SC-UC-22.md`
* Related Use Cases:
  * `Use Cases/UC-17.md` (geospatial ingestion)
  * `Use Cases/UC-18.md` (census ingestion + indicators)
  * `Use Cases/UC-19.md` (assessment ingestion)
  * `Use Cases/UC-20.md` (POI category standardization)
  * `Use Cases/UC-21.md` (deduplication)

## Assumptions (minimal)
* A scheduler/orchestrator exists (cron/workflow engine) and can trigger refresh workflows non-interactively.
* Each ingestion step supports staging + QA + atomic promotion semantics.
* Monitoring/alerting is configured (logs + metrics + notification channel).
* The system records:
  * workflow run ID
  * per-step run IDs (where applicable)
  * dataset production versions/metadata for traceability.

## Test Data Setup
Prepare a test environment with controllable outcomes:
* **R1 (Happy path)**: All steps succeed (where due) and publish.
* **R2 (Scheduler start failure)**: Misconfigured schedule/permission denial preventing workflow start.
* **R3 (Upstream failure)**: UC-17 fails so dependent steps (UC-20/UC-21) must skip/degrade per policy.
* **R4 (QA failure)**: One dataset fails QA and promotion is blocked; other independent steps may continue per policy.
* **R5 (Partial success)**: Some datasets are not due (skipped) and/or some fail; summary must be explicit.
* **R6 (Time window exceeded)**: A step exceeds time window/resource limits and workflow throttles/aborts per config.
* **R7 (Transient failure + retry)**: A step fails once (e.g., provider timeout) then succeeds on retry.
* **R8 (Secret missing/expired)**: A required secret is missing and workflow fails early.
* **R9 (Promotion failure)**: Promotion fails (DB lock/permissions) for one dataset; last known-good must remain intact.
* Ensure known last known-good production versions exist for each dataset before negative tests.

## Acceptance Test Suite (Gherkin-style)

### AT-22-01 — Scheduled workflow triggers at configured time and records workflow run ID
**Given** refresh schedules and dependencies are configured  
**When** the scheduled time occurs  
**Then** the scheduler triggers the refresh workflow  
**And** the system records a workflow run ID and start timestamp  
**And** the run is visible in logs/monitoring with status “running”.

### AT-22-02 — Workflow executes steps in dependency order
**Given** a workflow run starts in environment **R1**  
**When** the workflow executes  
**Then** steps run in the configured order (e.g., UC-17 → UC-20 → UC-21 → UC-18/UC-19 if due)  
**And** dependent steps do not run before their prerequisites complete successfully (unless explicit degrade policy allows it and is recorded).

### AT-22-03 — Each step runs non-interactively and captures per-step run IDs and dataset versions
**Given** a workflow run starts in **R1**  
**When** each step executes  
**Then** the step runs in automated mode (no interactive prompts)  
**And** a per-step run ID (or equivalent identifier) is recorded  
**And** dataset version/provenance metadata is recorded when the step promotes to production.

### AT-22-04 — QA gate blocks promotion and preserves last known-good production data
**Given** a workflow run in **R4** where a dataset fails QA  
**When** QA evaluates staging outputs  
**Then** promotion for that dataset is blocked  
**And** production remains on the last known-good version for that dataset  
**And** the workflow records the QA failure reason and surfaces it in the final summary and alerts.

### AT-22-05 — Upstream failure causes dependent steps to skip/degrade and records dependency chain
**Given** a workflow run in **R3** where UC-17 fails  
**When** the workflow evaluates dependent steps  
**Then** UC-20 and UC-21 are skipped (or degraded) according to policy  
**And** the workflow records the dependency failure chain  
**And** production remains unchanged for datasets not promoted.

### AT-22-06 — Partial success reporting is explicit and accurate
**Given** a workflow run in **R5** where some datasets are skipped (not due) and/or some fail  
**When** the workflow completes  
**Then** the final workflow summary explicitly lists:
* datasets promoted and their new versions
* datasets skipped and reasons (not due / dependency / policy)
* datasets failed and reasons (ingestion, QA, promotion, time window)  
**And** the overall status reflects partial success (e.g., `SUCCESS_WITH_WARNINGS` or `PARTIAL_SUCCESS`) rather than “success”.

### AT-22-07 — Retry policy handles transient failures and records attempts
**Given** a workflow run in **R7** with a transient failure  
**When** the failing step retries  
**Then** retries follow configured backoff/max attempts  
**And** attempt counts and timing are recorded in logs/metrics  
**And** if the step eventually succeeds, promotion occurs normally and the run summary includes the warning.

### AT-22-08 — Time window/resource limit enforcement throttles/aborts and alerts
**Given** a workflow run in **R6** where a step exceeds its time window/resource limits  
**When** limits are reached  
**Then** the workflow throttles/pauses/aborts according to configuration  
**And** an alert is emitted with the step name and limit exceeded  
**And** production remains unchanged for any dataset not successfully promoted.

### AT-22-09 — Scheduler start failure emits alert and no steps run
**Given** environment **R2** (scheduler misconfiguration/permissions)  
**When** the scheduled time occurs  
**Then** the workflow does not start  
**And** an alert is emitted identifying the job/workflow and reason  
**And** no ingestion steps run and production remains unchanged.

### AT-22-10 — Missing secret fails early with actionable error and preserves production
**Given** environment **R8** where a required secret is missing/expired  
**When** the workflow starts  
**Then** it fails early with an actionable error referencing the missing secret  
**And** no datasets are promoted  
**And** production remains unchanged.

### AT-22-11 — Promotion failure rolls back cleanly and preserves last known-good versions
**Given** a workflow run in **R9** where promotion fails for one dataset  
**When** promotion is attempted  
**Then** promotion failure is recorded with actionable DB error details  
**And** that dataset’s production version remains last known-good  
**And** the workflow summary indicates which datasets did/did not update.

### AT-22-12 — On-demand refresh run behaves like scheduled run
**Given** Sky triggers an on-demand refresh  
**When** the workflow runs  
**Then** it uses the same dependency ordering, QA gates, and atomic promotion semantics as scheduled runs  
**And** records workflow run ID, per-step identifiers, metrics, and final summary.

## Non-Functional Acceptance Criteria (verifiable)
* **Observability**: Logs/metrics include workflow run ID, per-step statuses, durations, counts, and warning/error details.
* **Reliability**: Failures do not corrupt production; last known-good data remains available for valuation.
* **Operational Clarity**: Alerts are emitted on start failures, ingestion failures, QA failures, promotion failures, and time window overruns with actionable diagnostics.
