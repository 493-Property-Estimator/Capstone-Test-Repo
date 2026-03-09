# Scenario — UC-19: Ingest property tax assessment data

## Scenario Name
Ingest assessment baselines and link them to canonical location IDs (with coverage QA and safe promotion)

## Narrative
Morgan is the PVE system maintainer responsible for keeping the system’s assessment baseline current, since estimates must be anchored to an official assessment value (UC-16). A new assessment release is published by the municipality, and Morgan initiates an ingestion run to bring the baseline forward to the newest assessment year.

Morgan wants confidence that the pipeline:
* captures and records provenance (assessment year, publish date, coverage notes, license)
* validates schema and key fields (assessment value + property identifiers/location)
* normalizes identifiers and currency fields into canonical formats
* links each record to the system’s canonical location ID reliably (parcel/address/spatial join), with explicit handling of ambiguous cases
* runs QA checks for coverage, duplicates, and outliers before publishing
* promotes atomically so valuation requests never see partial or inconsistent baselines
* preserves the last known-good baseline if ingestion, linking, QA, or promotion fails

## Scope
Property Value Estimator (PVE) — Data Sourcing & Assessment Baseline subsystem (Assessment Ingestion Pipeline + Linking/Geocoding + Assessment Store + Validation/QA + Scheduler)

## Actors
* **Primary Actor**: Maintainer (Morgan — Data Engineer / System Operator)
* **Supporting Actors**:
  * Open Data Provider (assessment dataset portal)
  * Ingestion Pipeline (download, validate, normalize, link, load)
  * Canonical Location Service (location ID strategy: parcel/address key, optional spatial join)
  * Geospatial Linking (parcels/boundaries; optional but common)
  * Database / Assessment Store (raw + normalized + linked, staging + production)
  * Validation/QA Module (schema, linking quality, coverage, outliers)
  * Scheduler (optional) and Notification channel (optional)
  * Logging/Monitoring (run IDs, metrics, alerts)

## Preconditions
* Assessment source endpoints/URLs and expected schemas are configured.
* Canonical location strategy exists (e.g., parcel ID, normalized address key, or spatial join to parcel polygons).
* Supporting reference data exists for linking (e.g., parcel polygons, address normalization rules, or crosswalk tables).
* Database schemas exist for:
  * raw assessment staging/production tables
  * normalized/linked assessment staging/production tables
  * lookup indexes by canonical location ID (for fast baseline retrieval)
  * run metadata/audit tables (including linking warnings and coverage metrics)
* A promotion mechanism exists (swap/rename or versioned views) for atomic publication.

## Trigger
Morgan starts an assessment ingestion run manually, or a scheduled refresh begins when a new release is detected.

## Main Flow (Success Scenario)
1. Morgan opens the ingestion control (CLI/UI) and selects “Assessment ingestion” for the configured assessment sources.
2. The system creates an ingestion **run ID** and records a configuration snapshot (source URLs, expected schema version, canonical linking strategy, QA thresholds).
3. The system fetches dataset metadata, including:
   * assessment year
   * publish date / refresh date
   * coverage notes (jurisdiction, included property classes if provided)
   * license/attribution note
4. The system downloads the assessment artifact(s) to staging and validates file integrity (parseable; size limits; checksum capture when available).
5. The system validates the dataset schema and key fields, including:
   * assessment value field exists and is numeric/currency-parseable
   * property identifier and/or address fields exist
   * required jurisdiction/geography fields exist if used for filtering/joins
6. The system normalizes assessment records into canonical internal formats:
   * standardizes currency units and numeric types
   * normalizes parcel identifiers and/or address formats (e.g., casing, abbreviations, postal code normalization)
   * handles missing/invalid entries per policy (drop, quarantine, or null + flags)
7. The system links each normalized assessment record to the system’s **canonical location ID** using the configured strategy:
   * direct match via parcel identifier when available
   * direct match via normalized address key when available
   * spatial join to parcel polygons/boundaries when geometry is provided or derivable
8. The system records linking outcomes for each record:
   * linked (high confidence)
   * linked (assumption/ambiguous) with a deterministic tie-break rule and warning flag
   * unlinked with a reason code (missing key, no match, multiple matches beyond threshold)
9. The system loads normalized and linked records into staging tables and builds lookup indexes by canonical location ID for fast retrieval.
10. The QA module runs checks on staging:
   * coverage: percentage of canonical locations with an assessment baseline
   * duplicates: multiple records mapping to the same canonical location handled per rule (e.g., highest confidence, latest year)
   * outliers: extremely high/low assessment values flagged (and compared to prior version where available)
   * linking quality: ambiguous-link rate below threshold; unlinked rate below threshold
11. The system records QA results, coverage metrics, and warnings in the run metadata and generates a summary report for Morgan.
12. The system promotes assessment staging → production atomically (swap/rename or versioned view update).
13. The system records production version metadata (assessment year, run ID, counts, coverage, warnings) and reports success.
14. Downstream valuation requests can retrieve baselines by canonical location ID and anchor estimates to the new assessment year (UC-16).

## Postconditions (Success)
* The assessment baseline for the new assessment year is queryable by canonical location ID.
* Baseline provenance (year/source/publish date) and run metadata (coverage, warnings) are recorded for auditability.
* Atomic promotion ensures readers only see a fully consistent baseline version.

## Variations / Extensions
* **4a — Download fails (provider downtime, URL changed)**
  * 4a1: The system retries with exponential backoff up to the configured limit.
  * 4a2: If still failing, the system marks the run failed and preserves the last known-good production baseline.
* **5a — Assessment schema changes (field renamed/removed)**
  * 5a1: The system fails validation and reports missing/changed fields.
  * 5a2: Morgan updates schema mappings and re-runs ingestion.
* **6a — Large fraction of invalid/missing values**
  * 6a1: The system quarantines invalid records (if supported) and reports counts and examples.
  * 6a2: If invalid rate exceeds threshold, QA fails and promotion is blocked.
* **7a — Linking ambiguity (multiple candidate parcels/addresses)**
  * 7a1: The system applies a deterministic confidence/tie-break rule (e.g., exact parcel ID match beats address match; closest centroid for spatial joins).
  * 7a2: The system flags ambiguous links for audit and includes an ambiguous-link rate in the run report.
  * 7a3: If ambiguity exceeds a threshold, QA fails and promotion is blocked.
* **7b — Condo/multi-unit properties**
  * 7b1: The system applies configured rules for mapping multiple units to a canonical location (e.g., building-level grouping or unit-level IDs) and records the rule used.
  * 7b2: The run report highlights how multi-unit records were handled.
* **10a — Coverage drop vs previous version**
  * 10a1: The QA module detects an abnormal coverage decrease compared to the last production version.
  * 10a2: The system blocks promotion and reports affected regions/keys and likely causes (linking failure, schema change, missing rows).
* **12a — Promotion fails (DB lock/permissions)**
  * 12a1: The system rolls back promotion and leaves existing production baseline intact.
  * 12a2: The system reports an actionable DB error and retains staging for inspection (if configured).
* **14a — Backfill multiple assessment years**
  * 14a1: Morgan selects multiple years to ingest (historical mode).
  * 14a2: The system versions each year and publishes a “latest” view used by default (unless a year is requested explicitly).

## Data Examples (Illustrative)
Example baseline record (illustrative only):
* Canonical location ID: `loc_001234`
* Assessment year: `2024`
* Assessment value: `$430,000`
* Source: `Municipal Assessment Dataset` (example)
* Link method: `parcel_id_direct` (example)
* Link confidence: `high` (example)
* Run ID: `assess_ingest_2026-02-12_001` (example)

Example run summary (illustrative only):
* Run ID: `assess_ingest_2026-02-12_001`
* Assessment year: `2024`
* Coverage: `92.1%` of canonical locations (example)
* Ambiguous links: `0.7%` (example)
* Promotion: `SUCCESS (atomic)`
* Warnings: `["Outliers flagged: 23 records"]`

## Business Rules / Guardrails (Product Requirements)
* A baseline must not be promoted unless schema validation and QA checks pass.
* Linking ambiguity must be handled deterministically and disclosed in run metadata (no silent many-to-one mapping without rules).
* Promotion must be atomic; production baseline must remain unchanged on failure.
* Baseline provenance must be recorded for every production version (year/source/publish date/run ID/counts/coverage/warnings).
* Duplicate mapping (multiple records per canonical location) must follow a deterministic resolution rule and be auditable.

## Acceptance Criteria (Checklist)
* Every run creates a run ID and records the configuration snapshot (source + linking strategy + QA thresholds).
* Assessment year and source/publish metadata are captured and stored.
* Schema and key-field validation blocks runs with missing/changed required fields.
* Normalization produces canonical currency and identifier formats with explicit handling of invalid/missing values.
* Linking yields coverage and ambiguity metrics and assigns reason codes for unlinked records.
* QA checks validate coverage, duplicates, outliers, and linking quality before promotion.
* Promotion is atomic; last known-good baseline remains intact on any failure.
* The success report includes year/version, counts, coverage, QA outcomes, and warnings.

## Notes / Assumptions
* Linking can be parcel-based, address-based, or spatial; the scenario assumes the approach is configuration-driven and can vary by jurisdiction.
* This ingestion provides the baseline used by UC-16; explainability and factor adjustments are handled downstream by the valuation engine.
