# Scenario — UC-18: Ingest municipal census datasets

## Scenario Name
Ingest municipal census data and publish neighbourhood indicators with coverage QA

## Narrative
Riley is the PVE system maintainer and needs neighbourhood indicators to stay current so users can compare areas and the valuation engine can use area-level context. Riley sees that a new municipal census release is available and wants to ingest it in a way that is repeatable and safe.

Riley expects the ingestion run to:
* fetch and record dataset provenance (year, geography level, refresh date, license/source)
* validate files, schema, and value constraints before any publication
* normalize the raw census tables into canonical internal schemas
* link census geographies to the system’s neighbourhood boundaries (or other internal area keys) with measurable coverage
* compute the project’s defined neighbourhood indicators (densities, household proxies, socioeconomic proxies where allowed)
* run QA checks (ranges, totals, join coverage thresholds) and block promotion if results are inconsistent
* promote indicator tables atomically so the UI/valuation never sees partial or inconsistent indicators

## Scope
Property Value Estimator (PVE) — Data Sourcing & Feature Store subsystem (Census Ingestion Pipeline + Boundary Linking + Indicator Computation + Database/Feature Store + Validation/QA + Scheduler)

## Actors
* **Primary Actor**: Maintainer (Riley — Data Engineer / System Operator)
* **Supporting Actors**:
  * Open Data Provider (municipal census portal)
  * Ingestion Pipeline (download, validate, normalize, load)
  * Boundary Dataset (neighbourhood polygons / internal area keys)
  * Database / Feature Store (raw imports + computed indicators, staging + production)
  * Indicator Computation Module (derivations and aggregations)
  * Validation/QA Module (schema, value constraints, coverage checks)
  * Scheduler (optional) and Notification channel (optional)
  * Logging/Monitoring (run IDs, metrics, alerts)

## Preconditions
* Census dataset sources, expected schemas, and mapping rules are configured (including field definitions and geography keys).
* Neighbourhood boundaries (or equivalent internal area keys) exist and are queryable for joins.
* Database schemas exist for:
  * raw census staging/production tables
  * computed indicator staging/production tables
  * run metadata/audit tables (including coverage and warnings)
* Indicator definitions are specified (which fields, formulas, units, and null-handling rules).
* Promotion mechanism exists to publish new indicators atomically (swap/rename or versioned views).

## Trigger
Riley starts a census ingestion run manually, or a scheduled job starts the run.

## Main Flow (Success Scenario)
1. Riley opens the ingestion control (CLI/UI) and selects “Census ingestion” for the configured municipal census sources.
2. The system creates an ingestion **run ID** and records the configuration snapshot (source URLs, expected schema version, boundary vintage, indicator definitions, QA thresholds).
3. The system fetches census dataset metadata for each artifact, such as:
   * collection year
   * geography level (e.g., neighbourhood, tract, dissemination area)
   * refresh/publish date
   * field definitions (when provided)
   * license/source attribution note
4. The system downloads census artifacts to a staging area and enforces download controls (size limits, retries, checksum capture when available).
5. The system validates each artifact:
   * file integrity/readability (parseable CSV/Excel/etc.)
   * required columns present (e.g., population, households; income proxies where available/allowed)
   * value constraints (non-negative counts, valid codes, required keys not null)
   * suppression/rounding markers handled according to policy (e.g., suppressed → null)
6. The system normalizes raw census data into canonical internal schemas:
   * standardizes column names and types
   * applies consistent units (counts vs rates) where applicable
   * converts missing/suppressed values into explicit nulls with provenance flags
7. The system links each census record to an internal area key:
   * direct join using geography codes where compatible, **or**
   * mapping-table join (old-to-new codes) when boundary or code systems changed
8. The system loads normalized raw census tables into **staging** tables, keyed by run ID and census year.
9. The indicator computation module computes neighbourhood indicators from the staged raw census data, producing indicator rows per area key (e.g., density, household size proxies, socioeconomic indicators where allowed).
10. The QA module validates the computed indicators:
   * totals/ranges are within expected bounds (e.g., no negative densities)
   * join coverage meets threshold (percentage of areas with computed indicators)
   * key indicator availability meets minimum requirements (required indicators present)
   * optional: compare to previous version for anomaly detection (e.g., large unexpected deltas)
11. The system records QA results, coverage metrics, and warnings in the run metadata and generates a summary report for Riley.
12. The system promotes indicator staging → production atomically (swap/rename or versioned view update).
13. The system records production version metadata (census year/version, run ID, coverage, warnings) and reports success.
14. Downstream services (valuation engine and UI “Neighbourhood info”) can query the new indicators immediately using the production tables/views.

## Postconditions (Success)
* Census data is stored in normalized internal schemas and linked to internal area keys.
* Neighbourhood indicators are computed, QA-validated, and published atomically to production.
* Run metadata provides provenance (year/source), coverage metrics, and QA outcomes for traceability.

## Variations / Extensions
* **4a — Download fails (provider downtime, URL changed)**
  * 4a1: The system retries with exponential backoff up to the configured limit.
  * 4a2: If still failing, the system marks the run failed and preserves the last known-good production indicators.
* **5a — Census artifact contains suppressed/rounded values**
  * 5a1: The system preserves suppressed values as nulls (and flags them) per policy.
  * 5a2: The system computes indicators with documented null-handling rules (e.g., omit from denominator, mark as “limited accuracy”).
  * 5a3: The run summary reports which indicators/areas are affected by suppression.
* **7a — Geography keys do not match boundaries (boundary changes)**
  * 7a1: The system attempts mapping via a configured mapping table.
  * 7a2: If mapping coverage is below threshold, the system blocks promotion and reports uncovered areas and missing mappings.
* **9a — Indicator computation fails**
  * 9a1: The system stops the run, reports which indicator(s) failed and why (e.g., division by zero, missing required fields).
  * 9a2: The system keeps existing production indicators unchanged.
* **10a — Coverage below threshold**
  * 10a1: The QA module fails the run and blocks promotion.
  * 10a2: The report highlights which areas are missing, whether missingness is due to join failure or suppressed values.
* **12a — Promotion fails (DB lock/permissions)**
  * 12a1: The system rolls back promotion and leaves production indicators intact.
  * 12a2: The system reports an actionable DB error and keeps staging for inspection (if configured).
* **1a — Scheduled run**
  * 1a1: The scheduler runs the ingestion using the same config snapshot and QA thresholds.
  * 1a2: The system emits success/failure to monitoring and triggers alerts on failure.

## Data Examples (Illustrative)
Example run summary (illustrative only):
* Run ID: `census_ingest_2026-02-12_001`
* Census year: `2021` (example)
* Geography level: `neighbourhood` (example)
* Boundary vintage: `2024-10` (example)
* Join coverage: `97.5%` of neighbourhoods mapped
* Promotion: `SUCCESS (atomic)`
* Warnings: `["Suppression present for income proxy fields"]`

Example indicator row (illustrative only):
* Area key: `neighbourhood:ritchie` (example)
* Population: `N`
* Population density: `N` people/km²
* Households: `N`
* Green space coverage (if computed elsewhere): `N%` (note: may depend on UC-17/other sources)
* Indicator metadata: `as_of_year=2021`, `source=municipal_census_portal`, `run_id=...`

## Business Rules / Guardrails (Product Requirements)
* Indicators must not be promoted unless QA passes and coverage thresholds are met.
* Suppressed/rounded census values must be handled explicitly (null + flags) and never treated as real zeros.
* Promotions must be atomic; production must not expose partial indicator updates.
* Provenance must be recorded (year, geography level, source, boundary vintage, run ID, coverage, warnings).
* If mapping between census geographies and boundaries is incomplete, the system must block promotion or clearly mark uncovered areas per policy (no silent gaps).

## Acceptance Criteria (Checklist)
* A run ID and configuration snapshot is recorded for every census ingestion run.
* Artifacts are validated for schema and value constraints before loading/publishing.
* Normalization produces canonical schemas with consistent types and explicit null handling.
* Geography-to-boundary linking is performed and coverage is computed and compared to thresholds.
* Indicators are computed successfully for expected areas and QA validates ranges/totals.
* Promotion is atomic; production indicators remain unchanged on any failure.
* The final report includes year/version, coverage metrics, QA outcomes, and warnings.

## Notes / Assumptions
* Some user-facing neighbourhood indicators (UC-12) may combine census-derived indicators (UC-18) with other sources (e.g., green space from geospatial datasets in UC-17); this scenario focuses on census ingestion and indicator publication.
* Exact indicator definitions and thresholds are configuration-driven and may evolve.
