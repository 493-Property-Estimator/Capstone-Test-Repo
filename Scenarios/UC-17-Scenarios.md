# Scenario — UC-17: Ingest open geospatial datasets

## Scenario Name
Ingest roads, boundaries, and POIs into the spatial database (with validation, QA, and atomic promotion)

## Narrative
Alex is the PVE system maintainer responsible for keeping the geospatial foundation data current and trustworthy. Before the valuation engine can compute distances, proximity, and coverage features, the system must have reliable baseline spatial context (roads, neighbourhood boundaries, and points-of-interest).

Alex initiates a geospatial ingestion run after noticing that the municipal portal has published updated boundary and POI files. Alex wants confidence that:
* every dataset is fetched from the configured open-data sources with traceable provenance (source/license/version)
* files are validated for integrity and schema/geometry correctness before being loaded
* transformations enforce canonical CRS and geometry conventions
* QA checks catch obvious data quality issues (coverage gaps, out-of-bounds geometries, duplicates, count anomalies)
* new data is promoted atomically so downstream feature computation never reads partial/invalid data
* failures preserve the last known-good production dataset and provide actionable diagnostics

## Scope
Property Value Estimator (PVE) — Data Sourcing & Database subsystem (Ingestion Pipeline + Spatial Database/Feature Store + Validation/QA + Scheduler)

## Actors
* **Primary Actor**: Maintainer (Alex — Data Engineer / System Operator)
* **Supporting Actors**:
  * Open Data Provider (municipal portal)
  * Ingestion Pipeline (download, validate, transform, load)
  * Staging Storage (temporary artifacts)
  * Spatial Database / Feature Store (staging + production tables)
  * Validation / QA Module (schema + geometry + sanity checks)
  * Scheduler (optional) and Notification channel (optional: email/Slack)
  * Logging/Monitoring (run IDs, metrics, alerts)

## Preconditions
* Source endpoints/URLs for roads, boundaries, and POIs are configured (and credentials/API keys if required).
* Canonical CRS and geometry rules are defined (e.g., EPSG code, geometry types per dataset).
* Spatial DB schemas exist for:
  * staging tables
  * production tables
  * ingestion run metadata/audit tables
* The ingestion runtime has enough storage/compute to download and transform artifacts within configured limits.
* An atomic promotion mechanism exists (swap/rename strategy) to avoid downtime and partial reads.

## Trigger
Alex starts an ingestion run manually, or a scheduled job starts an ingestion run.

## Main Flow (Success Scenario)
1. Alex opens the ingestion control (CLI/UI) and selects “Geospatial ingestion” for configured datasets: **roads**, **boundaries**, **POIs**.
2. The system creates an ingestion **run ID** and logs the configuration snapshot (source URLs, expected schemas, canonical CRS, QA thresholds).
3. The system fetches dataset metadata for each source, including:
   * source name/provider and dataset identifier
   * publish date/version (when provided)
   * license note/attribution requirement
   * file format (e.g., GeoJSON, Shapefile, GPKG)
   * expected geometry type and key fields
4. The system downloads each dataset artifact to a staging area and enforces controls:
   * maximum file size limits
   * checksum capture/verification (when available)
   * retry policy for transient failures
5. The system validates each downloaded artifact:
   * file integrity/readability (can be opened/parsed)
   * required fields/columns exist (IDs, names, category fields for POIs, etc.)
   * geometry validity checks (non-empty, valid geometries)
   * basic CRS detection (if embedded), or configuration-based CRS assumption with explicit logging
6. The system transforms each dataset to canonical standards:
   * reprojects to canonical CRS
   * normalizes geometry types:
     * roads → `MultiLineString`
     * boundaries → `Polygon`/`MultiPolygon`
     * POIs → `Point`
   * standardizes core fields (canonical IDs, names, categories, source timestamps, and source identifiers)
7. The system loads transformed data into **staging tables** in the spatial DB, keyed by the run ID/version.
8. The QA module runs checks on staging, such as:
   * row counts within expected bounds vs last known-good version
   * duplicate key detection (e.g., duplicate road IDs / POI IDs after normalization)
   * spatial sanity checks:
     * geometries fall within the target region extent
     * boundaries cover the expected area set (coverage threshold)
     * POIs/roads are not grossly out-of-bounds (e.g., lat/long swapped)
9. The system records QA results (pass/fail, warnings) attached to the run ID and produces a human-readable summary for Alex.
10. The system promotes staging → production using an **atomic swap** (e.g., rename/swap tables) so production readers either see the old version or the new version, but never an in-between state.
11. The system writes final ingestion metadata for auditability:
   * run ID, start/end timestamps
   * dataset versions/publish dates (when available)
   * counts (downloaded rows, loaded rows, rejected/repair counts)
   * warnings and QA outcomes
   * pointers to stored artifacts (if retained) and schema mapping versions
12. The system reports success to Alex (logs/UI), and downstream feature computation services can use the new spatial datasets immediately.

## Postconditions (Success)
* Roads, boundaries, and POIs exist in production spatial tables in canonical CRS/geometry formats.
* Ingestion provenance and QA results are recorded and traceable by run ID.
* Downstream feature computations use the newly promoted dataset versions without downtime.

## Variations / Extensions
* **3a — Source metadata missing or incomplete**
  * 3a1: The system proceeds using configured defaults (e.g., version = “unknown”) while recording the limitation.
  * 3a2: The run report includes a warning: “Source version metadata unavailable”.
* **4a — Download fails (provider downtime, URL changed, network outage)**
  * 4a1: The system retries with exponential backoff up to a configured limit.
  * 4a2: If still failing, the system marks the run failed, records which dataset failed, and preserves the last known-good production tables.
  * 4a3: Optional: the system sends an alert (notification channel) with the failed dataset and URL.
* **5a — Dataset format or schema changed unexpectedly**
  * 5a1: The validator detects missing/renamed fields or incompatible geometry types.
  * 5a2: The system fails the affected dataset and blocks promotion (no partial promotion of mixed-validity staging).
  * 5a3: Alex updates mapping/configuration and re-runs ingestion.
* **5b — CRS is not declared or does not match expectations**
  * 5b1: The system applies a configured CRS assumption and flags the run as “CRS assumed”.
  * 5b2: If spatial sanity checks indicate the assumption is wrong (e.g., out-of-bounds), the system blocks promotion and reports a CRS mismatch.
* **6a — Invalid geometries detected**
  * 6a1: The system attempts automated repairs within configured limits (e.g., make-valid / buffer(0) strategy depending on implementation).
  * 6a2: The system records repair counts and the repair rate.
  * 6a3: If the repair rate exceeds a threshold (data quality issue), the system fails the dataset and blocks promotion.
* **8a — QA checks fail (out-of-bounds geometries, count anomalies, coverage drop)**
  * 8a1: The system blocks promotion and keeps staging tables for inspection.
  * 8a2: The system produces a report identifying which QA rules failed (e.g., “POI count dropped 70% vs previous run”, “Boundary coverage below threshold”).
* **10a — Promotion fails (permissions, lock contention, low disk)**
  * 10a1: The system rolls back the promotion step and leaves production tables intact.
  * 10a2: The system reports the failure and includes the DB error detail for Alex.
* **1a — Scheduled ingestion run**
  * 1a1: The scheduler starts the run using the same configuration snapshot process.
  * 1a2: The system reports success/failure to monitoring and triggers alerts based on configured severity thresholds.
* **11a — Historical retention policy enabled**
  * 11a1: The system retains the last **N** successful versions (or full history) and records pointers to them.
  * 11a2: Alex can roll back to a prior version by selecting a previous run ID and promoting that version.

## Data Examples (Illustrative)
Example per-dataset ingestion metadata (illustrative only):
* Dataset: `boundaries_neighbourhoods`
  * Source: `Municipal Open Data Portal`
  * Publish date/version: `2026-01-30` (example)
  * Format: `GeoJSON`
  * Canonical CRS: `EPSG:XXXX` (example)
  * Loaded rows: `401` neighbourhood polygons
  * QA: `PASS` (warnings: `[]`)
* Dataset: `pois`
  * Loaded rows: `48,210`
  * Invalid geometries repaired: `12`
  * QA: `PASS` (warnings: `["CRS assumed"]`)
* Dataset: `roads`
  * Loaded rows: `9,870`
  * QA: `PASS` (warnings: `[]`)

Example run summary (illustrative only):
* Run ID: `geo_ingest_2026-02-12_001`
* Start/End: `2026-02-12T18:10:00Z` → `2026-02-12T18:26:40Z`
* Promotion: `SUCCESS (atomic swap)`
* Warnings: `["CRS assumed for POIs"]`

## Business Rules / Guardrails (Product Requirements)
* Datasets must be validated and QA-checked before promotion; failed QA blocks promotion.
* Promotion must be atomic; the system must not expose partial staging data to production readers.
* Partial/invalid datasets must not replace the last known-good production version.
* Provenance must be recorded per dataset and per run (source, version/publish date when available, run timestamps, row counts, warnings).
* Geometry must be stored in canonical CRS and normalized geometry types to keep downstream feature computation consistent.

## Acceptance Criteria (Checklist)
* A run ID is created and logged for every ingestion attempt.
* Each dataset records provenance (source, publish date/version if available, license note) in run metadata.
* Downloads enforce size limits and record checksums when available; retries occur on transient failures.
* Validation fails fast on unreadable artifacts or missing required fields; promotion is blocked.
* Canonical CRS reprojection and geometry normalization are applied consistently for roads/boundaries/POIs.
* QA checks run on staging and block promotion when thresholds fail (count anomalies, out-of-bounds geometries, coverage drops).
* Promotion is atomic; production tables are unchanged if promotion fails.
* The success report includes counts, warnings, QA outcomes, and promotion status.

## Notes / Assumptions
* Exact CRS code, field mappings, and QA thresholds are configuration-driven and will vary by jurisdiction and source.
* Canonical POI category standardization may be handled separately (UC-20), but UC-17 ensures raw categories are captured and POIs are spatially valid and queryable.
