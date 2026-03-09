# Scenario — UC-22: Schedule open-data refresh jobs

## Scenario Name
Schedule and run automated refresh workflows (with dependencies, QA gates, alerts, and safe publication)

## Narrative
Sky is the PVE system operator responsible for keeping open-data inputs current so valuation features and user-facing indicators remain accurate over time. Different datasets refresh on different cadences (geospatial and POIs more frequently, assessment and census less frequently), and refreshes must be safe: a failed run must not corrupt production data.

Sky configures refresh schedules and dependencies so the system refreshes itself without manual intervention. Sky wants confidence that:
* refresh workflows run on time and can also be triggered on-demand
* steps execute in a safe dependency order (e.g., boundaries/POIs before derived indicators)
* each ingestion step runs non-interactively (automated mode) and publishes only after QA passes
* partial success is reported clearly (what updated, what stayed on older versions)
* failures emit alerts with diagnostic details and preserve last known-good production datasets
* the system records versions/run IDs so any estimate can be traced to the data versions used

## Scope
Property Value Estimator (PVE) — Operations, Scheduling, and Data Refresh subsystem (Scheduler/Orchestrator + Ingestion Pipelines + Feature Store/DB + Monitoring/Alerting)

## Actors
* **Primary Actor**: Maintainer (Sky — System Operator)
* **Supporting Actors**:
  * Scheduler/Orchestrator (cron / workflow engine)
  * Ingestion Pipelines:
    * Geospatial ingestion (UC-17)
    * Census ingestion + indicators (UC-18)
    * Assessment ingestion (UC-19)
    * POI category standardization (UC-20)
    * Entity deduplication (UC-21)
  * Database / Feature Store (staging + production tables/views)
  * Monitoring/Alerting (logs, metrics, notifications)
  * Secrets Manager (optional; API keys/credentials)
  * Open Data Providers (municipal portals)

## Preconditions
* UC-17/UC-18/UC-19 are implemented and runnable in automated (non-interactive) mode.
* Scheduler/orchestrator is deployed and permitted to:
  * trigger jobs
  * access required secrets
  * write logs/metrics
* Safe data publishing strategy exists (staging + atomic promotion) for all ingestion steps.
* Monitoring/alerting channels are configured (dashboard + notifications).
* Job dependency policy is defined (skip/degrade/abort on upstream failures).

## Trigger
* Sky configures refresh schedules/policies, or
* the scheduler triggers a refresh run at the configured time, or
* Sky manually triggers an on-demand refresh (e.g., after adding a new source).

## Main Flow (Success Scenario)
1. Sky defines refresh policies per dataset type, such as:
   * geospatial datasets (roads/boundaries/POIs): weekly
   * POI category standardization: after POI ingestion completes
   * POI deduplication: after standardization completes (or after adding a source)
   * census indicators: annually (or when a new release is detected)
   * assessment baselines: annually (or when a new release is detected)
2. Sky configures the scheduler with a workflow definition that includes:
   * job schedules and time windows
   * dependencies and ordering
   * retry policies and backoff
   * resource limits and concurrency rules
   * alerting rules (warning vs critical)
3. At the scheduled time, the scheduler triggers a refresh workflow and assigns a workflow **run ID**.
4. The workflow initializes and records a configuration snapshot (schedules, dataset sources, pipeline versions, thresholds) for traceability.
5. The workflow executes ingestion steps in the configured dependency order. A typical order is:
   1) UC-17 ingest geospatial datasets (includes POIs)
   2) UC-20 standardize POI categories
   3) UC-21 deduplicate POIs into canonical entities
   4) UC-18 ingest census datasets and compute indicators (if due)
   5) UC-19 ingest assessment baselines (if due)
6. For each step, the system:
   * writes outputs to staging tables
   * runs validation/QA gates and checks promotion criteria
   * promotes to production atomically on success
   * records dataset version metadata (source version/publish date when available, run IDs, row counts, warnings)
7. The workflow collects run metrics and emits them to monitoring:
   * start/end timestamps and duration
   * per-step success/failure and retries
   * counts (rows loaded, mapped/unmapped, merges performed)
   * QA warnings and anomalies
8. The system generates a final workflow summary for Sky:
   * which datasets were refreshed and their new production versions
   * which datasets were skipped (not due) and why
   * any warnings produced during refresh
9. Sky receives a success notification (dashboard/notification channel) and can drill into logs by workflow run ID and per-step run IDs.
10. Updated production datasets are available for valuation engine feature computation immediately after promotion.

## Postconditions (Success)
* Refresh jobs run on schedule and update the intended datasets/indicators in production.
* All promotions are atomic; production contains a coherent set of versions per dataset.
* Run IDs and version metadata exist to trace estimates back to dataset versions used.

## Variations / Extensions
* **3a — Job start fails (scheduler misconfiguration / missing permissions)**
  * 3a1: The scheduler reports a start failure and emits an alert with the failing job/workflow and reason.
  * 3a2: No ingestion steps run; production remains unchanged.
* **4a — Required secret missing/expired**
  * 4a1: The workflow fails early, records the missing secret reference, and alerts Sky.
  * 4a2: Production remains unchanged.
* **5a — Upstream dataset ingestion fails; dependent steps follow policy**
  * 5a1: If UC-17 fails, UC-20/UC-21 are skipped (no new POIs to classify/dedupe).
  * 5a2: If UC-18 depends on boundaries and boundaries were not refreshed, UC-18 runs using last known-good boundaries only if policy allows; otherwise UC-18 is skipped.
  * 5a3: The workflow records the dependency chain and alerts Sky.
* **6a — QA gate fails for a dataset**
  * 6a1: Promotion for that dataset is blocked; production keeps the last known-good version.
  * 6a2: Staging outputs are retained for debugging (if configured).
  * 6a3: The workflow continues with independent steps if allowed, and reports partial success.
* **6b — Partial refresh succeeds**
  * 6b1: The workflow promotes only datasets that passed QA.
  * 6b2: The final report clearly lists datasets still on older versions and the reason (failed QA, skipped by dependency, not due).
* **7a — Refresh exceeds time window or resource limits**
  * 7a1: The workflow throttles/pauses/aborts per configuration.
  * 7a2: Sky receives an alert including which step exceeded the window and which datasets were (not) promoted.
* **8a — Missed schedule / backfill policy**
  * 8a1: If a run is missed (scheduler downtime), the system either runs immediately on recovery or waits until the next window per policy.
  * 8a2: The system records the missed run and backfill decision in monitoring.
* **10a — On-demand refresh**
  * 10a1: Sky triggers the workflow manually (e.g., after adding a new POI source).
  * 10a2: The workflow runs with the same QA gates and promotion semantics as scheduled runs.

## Data Examples (Illustrative)
Example refresh policy configuration (illustrative only):
* `geospatial_refresh`: weekly Sunday 02:00
* `poi_standardize`: triggered after geospatial_refresh success
* `poi_dedupe`: triggered after poi_standardize success
* `census_refresh`: yearly (or manual)
* `assessment_refresh`: yearly (or manual)

Example workflow run summary (illustrative only):
* Workflow run ID: `refresh_2026-02-12_0200`
* UC-17: `SUCCESS` (run ID `geo_ingest_...`, warnings `[]`)
* UC-20: `SUCCESS` (run ID `poi_cat_...`, unmapped `3.8%`)
* UC-21: `SUCCESS` (run ID `poi_dedupe_...`, review candidates `1,120`)
* UC-18: `SKIPPED (not due)`
* UC-19: `SKIPPED (not due)`
* Overall: `SUCCESS_WITH_WARNINGS`

## Business Rules / Guardrails (Product Requirements)
* Scheduled workflows must run ingestion use cases non-interactively and with explicit dependency ordering.
* Every ingestion step must gate promotion on QA; failed QA blocks promotion and preserves last known-good production data.
* Promotions must be atomic per dataset; partial/invalid staging data must never be visible to production readers.
* The system must emit structured logs/metrics and alerts on failures and significant warnings.
* Version/run metadata must be recorded for every promoted dataset so downstream estimates can be traced.
* Partial success must be explicitly reported (no silent “success” when some datasets stayed on old versions).

## Acceptance Criteria (Checklist)
* Sky can configure schedules and dependencies for each dataset refresh workflow.
* Scheduler triggers workflows at configured times and records a workflow run ID.
* Each pipeline step runs in automated mode and records a per-step run ID and dataset version metadata.
* QA failures block promotion for the failing dataset while leaving production unchanged.
* Dependent steps are skipped/degraded according to configured policy and are reported with reasons.
* Alerts are emitted for start failures, ingestion failures, QA failures, and time-window overruns.
* Final workflow summary lists updated datasets, skipped datasets, and datasets that remained on older versions (with reasons).

## Notes / Assumptions
* The choice of scheduler (cron vs workflow engine) is implementation-specific; this scenario assumes the system can record run IDs and structured status for each job.
* Cadences vary by jurisdiction and source; policies should be configurable and may evolve as data sources change.
