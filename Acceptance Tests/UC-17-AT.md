# Acceptance Tests — UC-17: Ingest open geospatial datasets

## Purpose
Verify that the system can ingest open geospatial datasets (roads, boundaries, POIs) end-to-end: fetch metadata, download artifacts, validate schema/geometry, transform to canonical CRS and geometry conventions, load into staging, run QA checks, and promote atomically to production with provenance/versioning recorded. Verify safe failure behavior that preserves last known-good production data.

## References
* User Story: **US-17: Ingest open geospatial datasets**
* Use Case: `Use Cases/UC-17.md`
* Scenario: `Scenarios/SC-UC-17.md`
* Related Use Case: `Use Cases/UC-20.md` (standardize POI categories; UC-17 ensures raw categories and spatial validity)

## Assumptions (minimal)
* Ingestion is runnable manually (CLI/UI) and optionally by scheduler.
* The pipeline uses **staging tables** and a **promotion** step (swap/rename) to update production atomically.
* The system records ingestion run metadata (run ID, timestamps, dataset source/version, counts, warnings, QA outcomes).
* Canonical CRS and expected geometry types per dataset are defined by configuration.

## Test Data Setup
Prepare controlled sources and environments for repeatable tests:
* **S1 (Happy path sources)**: Valid roads/boundaries/POIs artifacts with declared CRS and stable schema.
* **S2 (Download failure)**: Source URL that times out / returns 5xx / missing file.
* **S3 (Schema change)**: Artifact missing required fields or with renamed fields.
* **S4 (Invalid geometry)**: Artifact with invalid/corrupt geometries above/below repair threshold.
* **S5 (CRS mismatch/unknown CRS)**: Artifact with wrong CRS or no CRS declaration.
* **S6 (QA fail)**: Artifact that causes count anomaly, out-of-bounds geometries, or boundary coverage drop beyond threshold.
* **S7 (Promotion failure)**: Induced DB failure (permissions/lock contention) during promotion.
* A known **last known-good** production version exists before each negative test so preservation can be verified.

## Acceptance Test Suite (Gherkin-style)

### AT-17-01 — End-to-end ingest success for roads, boundaries, and POIs
**Given** the maintainer initiates a geospatial ingestion run using **S1**  
**When** the pipeline completes  
**Then** the system reports success for roads, boundaries, and POIs  
**And** transformed data is present in production tables  
**And** ingestion metadata is recorded including run ID, start/end timestamps, dataset source identifiers, and row counts.

### AT-17-02 — Provenance metadata is captured for each dataset
**Given** a successful ingestion run using **S1**  
**When** the maintainer inspects the run report/metadata  
**Then** each dataset (roads/boundaries/POIs) includes provenance fields such as:
* source/provider and dataset identifier/name
* publish date/version (when available) or “unknown” with a warning
* license/attribution note (when available)
* file format and ingestion timestamp

### AT-17-03 — Download controls: size limits, checksums, and retries are enforced
**Given** ingestion is started  
**When** a dataset download occurs  
**Then** the system enforces configured size limits  
**And** captures/records checksums when available (or records that checksums are unavailable)  
**And** transient download failures are retried according to configured backoff and max-attempt limits.

### AT-17-04 — Validation blocks promotion when required fields are missing (schema validation)
**Given** ingestion is started with **S3** (missing/renamed required fields)  
**When** the system validates the artifact  
**Then** the system marks the dataset as failed with actionable details about missing/changed fields  
**And** the ingestion run does not promote any partial/invalid data to production  
**And** the last known-good production tables remain unchanged.

### AT-17-05 — Geometry validation and repair behavior is transparent and thresholded
**Given** ingestion is started with **S4** containing invalid geometries  
**When** validation/repair runs  
**Then** the system either:
* repairs invalid geometries within configured limits and records repair counts, **or**
* fails the dataset if invalid/repair rate exceeds the configured threshold  
**And** if the dataset fails, promotion is blocked and last known-good production data remains in place.

### AT-17-06 — Canonical CRS reprojection is applied and verifiable
**Given** ingestion is started with **S1** (declared CRS)  
**When** transformation completes  
**Then** the stored geometries are in the configured canonical CRS  
**And** the run metadata records the input CRS (when known) and the canonical CRS used  
**And** CRS mismatches are not silently accepted without warnings.

### AT-17-07 — CRS missing or mismatch triggers warnings and/or blocks promotion via spatial sanity checks
**Given** ingestion is started with **S5** (unknown/wrong CRS)  
**When** the system applies CRS assumptions or detects mismatch  
**Then** the run report includes an explicit CRS warning (e.g., “CRS assumed”)  
**And** if spatial sanity checks indicate out-of-bounds results, the system fails QA and blocks promotion  
**And** last known-good production tables remain intact.

### AT-17-08 — Geometry type normalization is enforced per dataset
**Given** a successful ingestion run using **S1**  
**When** the maintainer inspects transformed outputs (or schema expectations)  
**Then** roads are stored as `MultiLineString` (or configured road geometry type)  
**And** boundaries are stored as `Polygon`/`MultiPolygon`  
**And** POIs are stored as `Point`  
**And** mixed/incorrect geometry types are rejected or normalized per configured rules with warnings.

### AT-17-09 — QA checks catch count anomalies, out-of-bounds data, duplicates, and coverage drops
**Given** ingestion is started with **S6** designed to trigger QA failures  
**When** QA checks run on staging tables  
**Then** the system reports which QA rules failed (e.g., count delta, duplicate IDs, out-of-bounds, coverage below threshold)  
**And** promotion is blocked  
**And** staging data is retained for inspection (if configured) while production remains unchanged.

### AT-17-10 — Atomic promotion: readers never see a partially updated production state
**Given** a successful ingestion run using **S1**  
**When** promotion occurs  
**Then** production updates occur atomically (swap/rename)  
**And** there is no period where some datasets are updated while others remain old (unless partial promotion is explicitly allowed and clearly versioned)  
**And** the run report includes promotion status and timing.

### AT-17-11 — Promotion failure rolls back cleanly and preserves last known-good data
**Given** ingestion passes validation and QA on staging  
**And** promotion is forced to fail using **S7** (DB permissions/locks)  
**When** the system attempts promotion  
**Then** the system reports promotion failure with actionable DB error details  
**And** production tables remain at the last known-good version  
**And** the run is marked failed (or “promotion failed”) and not recorded as a successful production version.

### AT-17-12 — Scheduled ingestion run behaves the same as manual run (if scheduler enabled)
**Given** the scheduler is enabled and configured to run UC-17 ingestion  
**When** a scheduled run starts  
**Then** the system produces the same run metadata (run ID, config snapshot, counts, QA outcomes) as a manual run  
**And** success/failure is emitted to monitoring/alerts according to configuration.

### AT-17-13 — Repeatability: fixed sources/config yield consistent outputs and metadata
**Given** ingestion is run multiple times against the same **S1** artifacts and configuration  
**When** runs complete successfully  
**Then** row counts and core derived fields are consistent within expected tolerances  
**And** the system records distinct run IDs and timestamps  
**And** the same dataset version metadata is recorded when source version is unchanged.

## Non-Functional Acceptance Criteria (verifiable)
* **Performance**: Ingestion completes within an agreed window for target dataset sizes (e.g., within X minutes) under normal conditions.
* **Reliability**: Failures (download/validation/QA/promotion) are detected, logged with actionable details, and do not corrupt production.
* **Auditability**: Every run is traceable via run ID and records dataset provenance, QA outcomes, warnings, and promotion status.
