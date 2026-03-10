# Feature Specification: Ingest open geospatial datasets

**Feature Branch**: `017-geospatial-ingest`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-17.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-17-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-17-AT.md Hard rules: 1) Copy the use case flows directly into spec.md (main + alternate + exception flows). Preserve ordering and intent. Do not invent steps. 2) You may make style/grammar improvements only if meaning is unchanged. 3) Extract functional requirements (FRs) ONLY from: - the flows in UC-17.md, and - the checks/expectations in UC-17-AT.md Do not add “nice-to-have” requirements that aren’t supported by those sources. 4) Keep implementation constraints: Python, vanilla HTML/CSS/JS. 5) Treat this use case as its own feature branch (branch naming suggestion is fine, but don’t actually run git commands unless asked). Spec contents required: - Feature name (from use case title) - Summary / goal - Actors - Preconditions - Triggers - Main flow (verbatim from use case) - Alternate flows (verbatim) - Exception/error flows (verbatim) - Data involved (only what the use case mentions) - Functional requirements list (numbered FR-01-001, FR-01-015, ...) - Traceability section mapping: - each acceptance test → related FRs - each flow step (or flow section) → related FRs (coarse mapping is fine) Output: - Update/produce the spec.md for this feature. If Spec-Kit expects a per-feature folder/file, follow the tool's convention, but the content must match the above constraints."

## Summary

Enable a maintainer to ingest open geospatial datasets for roads, boundaries, and points of interest so downstream spatial feature computation has validated, canonical, and traceable source data.

## Goal

The maintainer ingests open geospatial datasets (roads, boundaries, and points-of-interest) into the system's database so downstream feature computation (distance, proximity, coverage) has baseline spatial context.

## Actors

- **Primary Actor**: Maintainer (Data Engineer / System Operator)
- **Secondary Actors**: Open Data Provider (municipal portal), Ingestion Pipeline, Spatial Database/Feature Store, Validation/QA Module, Scheduler (optional)

## Preconditions

- Source endpoints and dataset URLs are configured (including any required API keys, if applicable).
- The spatial database is reachable and has required schemas/tables (or migrations can create them).
- The ingestion pipeline has access to sufficient storage/compute for downloading and processing datasets.
- Canonical coordinate reference system (CRS) and geometry rules are defined (e.g., how to store points vs polygons).

## Trigger

The maintainer starts an ingestion run (manual) or a scheduled job starts an ingestion run.

## User Scenarios & Testing

### User Story 1 - Ingest validated geospatial data (Priority: P1)

As a maintainer, I want roads, boundaries, and POI datasets fetched, validated, transformed, and loaded into production safely so downstream feature computation can rely on current spatial context.

**Why this priority**: This is the core value of UC-17 and the minimum independently useful slice.

**Independent Test**: Run ingestion against valid source artifacts and verify that production tables contain transformed datasets and that ingestion metadata is recorded.

**Acceptance Scenarios**:

1. **Given** a maintainer starts ingestion with valid configured sources, **When** the pipeline completes, **Then** the system reports success and production tables contain transformed roads, boundaries, and POIs.
2. **Given** a successful run, **When** the maintainer inspects run metadata, **Then** provenance, versions, counts, and timing information are recorded for each dataset.

### User Story 2 - Prevent bad data from replacing production (Priority: P2)

As a maintainer, I want download, schema, geometry, CRS, QA, and promotion failures to block unsafe promotion so the last known-good production data remains usable.

**Why this priority**: Safe failure behavior is essential because ingesting invalid spatial data would corrupt downstream computations.

**Independent Test**: Run ingestion against negative fixtures for download failure, schema change, invalid geometry, CRS mismatch, QA failure, and promotion failure, then verify that promotion is blocked and production remains unchanged.

**Acceptance Scenarios**:

1. **Given** a dataset download or validation failure occurs, **When** ingestion processes the dataset, **Then** the system reports actionable failure details and does not promote partial or invalid data.
2. **Given** QA checks or promotion fail, **When** the pipeline reaches those stages, **Then** staging is handled per the source rules and production remains at the last known-good version.

### User Story 3 - Trace and repeat ingestion runs (Priority: P3)

As a maintainer, I want each ingestion attempt to be traceable and repeatable so I can audit data provenance and compare runs over time.

**Why this priority**: Run-level provenance and repeatability are required for auditability and troubleshooting.

**Independent Test**: Execute repeated runs with unchanged inputs and verify distinct run IDs, stable dataset version metadata, and consistent counts within expected tolerances.

**Acceptance Scenarios**:

1. **Given** a successful or failed run, **When** the maintainer reviews the run report, **Then** the system exposes run identifiers, provenance, warnings, QA outcomes, and promotion status.
2. **Given** the same artifacts and configuration are ingested repeatedly, **When** runs complete, **Then** the outputs and recorded version metadata stay consistent within expected tolerances.

### Edge Cases

- Dataset downloads can fail because of network outages, provider downtime, or changed URLs.
- Dataset schema, geometry, or CRS can change unexpectedly and require warnings, repair attempts, or blocked promotion.
- QA checks can fail because of count anomalies, duplicate identifiers, out-of-bounds geometries, or coverage drops.
- Promotion can fail because of permissions or lock contention, and production must remain on the last known-good version.

## Main Flow

### Main Success Scenario

1. The maintainer initiates a geospatial ingestion run for the configured sources (roads, boundaries, POIs).
2. The system retrieves dataset metadata (source name, publish date/version, license note, file format, expected schema).
3. The system downloads the dataset artifacts to a staging area (with checksums and size limits enforced).
4. The system validates each artifact:
    * file integrity and readability
    * required columns/attributes exist
    * geometry validity checks (non-empty, valid geometries)
5. The system transforms each dataset to canonical standards:
    * reprojects to canonical CRS
    * normalizes geometry types (e.g., MultiLineString for roads, Polygon/MultiPolygon for boundaries, Point for POIs)
    * standardizes core fields (IDs, names, categories, update timestamps)
6. The system loads transformed data into staging tables in the spatial database.
7. The system runs QA checks on staging:
    * row counts within expected bounds
    * spatial sanity checks (geometries fall within target region boundaries)
    * duplicate primary keys/IDs detection
8. The system promotes staging tables to production tables (swap/rename) to avoid downtime and ensure atomic updates.
9. The system records ingestion metadata (source, version, run timestamp, counts, warnings) for audit and troubleshooting.
10. The system reports success to the maintainer (logs/UI) and makes data available for feature computations.

## Alternate Flows

None.

## Exception/Error Flows

- **3a**: Download fails (network outage, provider downtime, URL changed)
  - 3a1: The system retries with exponential backoff up to a configured limit.
  - 3a2: If still failing, the system marks the run failed and preserves the last known-good production dataset.
- **4a**: Dataset format/schema changed unexpectedly
  - 4a1: The system marks the affected dataset as failed, reports which fields/geometry types were unexpected, and does not promote data.
  - 4a2: The maintainer updates the source configuration and mapping rules, then re-runs ingestion.
- **4b**: Geometry is invalid or corrupted beyond repair
  - 4b1: The system attempts automated fixes (e.g., geometry repair) within configured limits.
  - 4b2: If repair rate exceeds a threshold, the system fails the dataset and emits a warning indicating data quality issues.
- **7a**: QA checks fail (out-of-bounds geometries, severe count anomalies)
  - 7a1: The system blocks promotion, keeps staging for inspection, and reports which QA rules failed.
- **8a**: Promotion fails (DB permissions, lock contention)
  - 8a1: The system rolls back the promotion step, leaves existing production tables intact, and reports the failure.

## Data Involved

- Configured source endpoints and dataset URLs.
- Dataset metadata including source name, publish date/version, license note, file format, and expected schema.
- Downloaded dataset artifacts in the staging area.
- Checksums and size-limit results for downloaded artifacts.
- Artifact validation results including file integrity, readability, required fields, and geometry validity.
- Canonical CRS and geometry rules.
- Transformed dataset content with normalized geometry types and standardized fields such as IDs, names, categories, and update timestamps.
- Staging tables and production tables in the spatial database.
- QA results including row-count checks, spatial sanity checks, and duplicate ID detection.
- Ingestion metadata including source, version, run timestamp, counts, warnings, and failure details.

## Requirements

### Functional Requirements

- **FR-01-001**: The system MUST allow a maintainer to start a geospatial ingestion run for configured roads, boundaries, and POI sources, either manually or through a scheduled job.
- **FR-01-002**: The system MUST retrieve dataset metadata for each configured dataset, including source name, publish date or version, license note, file format, and expected schema.
- **FR-01-003**: The system MUST download dataset artifacts to a staging area and enforce configured size limits during download.
- **FR-01-004**: The system MUST capture checksums when available and enforce the configured retry and backoff behavior for transient download failures.
- **FR-01-005**: The system MUST validate each downloaded artifact for integrity, readability, required columns or attributes, and non-empty valid geometries before promotion can proceed.
- **FR-01-006**: The system MUST transform each dataset to canonical standards by reprojecting to the canonical CRS, normalizing geometry types, and standardizing core fields.
- **FR-01-007**: The system MUST load transformed data into staging tables in the spatial database before any promotion to production occurs.
- **FR-01-008**: The system MUST run QA checks on staging that include row-count bounds, spatial sanity checks, and duplicate key or ID detection.
- **FR-01-009**: The system MUST promote staging tables to production atomically so production readers do not observe a partially updated state.
- **FR-01-010**: The system MUST record ingestion metadata for each run, including run identifier, timestamps, dataset provenance, counts, warnings, QA outcomes, and promotion status.
- **FR-01-011**: If a dataset download continues to fail after configured retries, the system MUST mark the run failed and preserve the last known-good production dataset.
- **FR-01-012**: If dataset format or schema changes unexpectedly, the system MUST fail the affected dataset with actionable details and MUST NOT promote partial or invalid data to production.
- **FR-01-013**: If invalid geometries are detected, the system MUST attempt automated repair only within configured limits, record repair counts or warnings, and fail the dataset if the repair rate exceeds the configured threshold.
- **FR-01-014**: If CRS information is missing or mismatched, the system MUST record an explicit CRS warning when assumptions are applied and MUST block promotion if spatial sanity checks indicate the assumption or mismatch produces invalid spatial results.
- **FR-01-015**: If QA checks fail, the system MUST block promotion, report which QA rules failed, and preserve the last known-good production data.
- **FR-01-016**: If promotion fails, the system MUST roll back the promotion step, leave existing production tables intact, and report actionable failure details.
- **FR-01-017**: When scheduler-based ingestion is enabled, scheduled runs MUST produce the same run metadata and success or failure reporting behavior as manual runs.
- **FR-01-018**: Repeated ingestion runs against the same artifacts and configuration MUST record distinct run IDs and timestamps while keeping row counts, core derived fields, and dataset version metadata consistent within expected tolerances.

### Non-Functional Requirements

- **NFR-01**: Ingestion MUST complete within the agreed operational window for target dataset sizes under normal conditions.
- **NFR-02**: Download, validation, QA, and promotion failures MUST be detected and reported with actionable details without corrupting production data.
- **NFR-03**: Every ingestion run MUST be auditable through recorded run identifiers, provenance metadata, QA outcomes, warnings, and promotion status.

### Key Entities

- **Ingestion Run**: A single manual or scheduled ingestion attempt with its run identifier, timing, status, warnings, and outcomes.
- **Geospatial Dataset**: One configured source dataset for roads, boundaries, or points of interest together with its source metadata and artifact.
- **Staging Dataset**: The transformed and validated dataset loaded into staging tables prior to QA and promotion.
- **Run Report**: The recorded provenance, validation, QA, counts, and promotion results used for audit and troubleshooting.

## Success Criteria

### Measurable Outcomes

- **SC-01**: In 100% of successful ingestion runs, roads, boundaries, and POIs are available in production tables and the run report records run ID, timestamps, provenance, and row counts.
- **SC-02**: In 100% of schema, geometry, CRS, QA, and promotion failure test cases, promotion is blocked or rolled back and the last known-good production data remains unchanged.
- **SC-03**: In 100% of successful runs, the maintainer can inspect per-dataset provenance including source, version or publish date when available, file format, and ingestion timestamp.
- **SC-04**: For repeated runs against unchanged source artifacts and configuration, row counts and core derived fields remain consistent within expected tolerances while each run records a distinct run ID and timestamp.

## Assumptions

- The scenario file was used only to clarify terminology and operational context; the use case and acceptance tests remain the source of truth.
- Historical retention policy and rollback-to-prior-version behavior are not required in this feature unless a later source explicitly adds them.

## Traceability

### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-17-01 | FR-01-001, FR-01-006, FR-01-009, FR-01-010 |
| AT-17-02 | FR-01-002, FR-01-010 |
| AT-17-03 | FR-01-003, FR-01-004, FR-01-011 |
| AT-17-04 | FR-01-005, FR-01-012 |
| AT-17-05 | FR-01-005, FR-01-013 |
| AT-17-06 | FR-01-006, FR-01-014 |
| AT-17-07 | FR-01-014, FR-01-015 |
| AT-17-08 | FR-01-006 |
| AT-17-09 | FR-01-008, FR-01-015 |
| AT-17-10 | FR-01-009, FR-01-010 |
| AT-17-11 | FR-01-016 |
| AT-17-12 | FR-01-001, FR-01-010, FR-01-017 |
| AT-17-13 | FR-01-010, FR-01-018 |

### Flow Steps and Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow 1 | FR-01-001 |
| Main Flow 2 | FR-01-002 |
| Main Flow 3 | FR-01-003, FR-01-004 |
| Main Flow 4 | FR-01-005 |
| Main Flow 5 | FR-01-006 |
| Main Flow 6 | FR-01-007 |
| Main Flow 7 | FR-01-008 |
| Main Flow 8 | FR-01-009 |
| Main Flow 9 | FR-01-010 |
| Main Flow 10 | FR-01-010 |
| Exception Flow 3a | FR-01-004, FR-01-011 |
| Exception Flow 4a | FR-01-012 |
| Exception Flow 4b | FR-01-013 |
| Exception Flow 7a | FR-01-015 |
| Exception Flow 8a | FR-01-016 |
