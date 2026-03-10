# Feature Specification: Ingest municipal census datasets

**Feature Branch**: `018-census-ingest`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-18.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-18-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-18-AT.md Hard rules: 1) Copy the use case flows directly into spec.md (main + alternate + exception flows). Preserve ordering and intent. Do not invent steps. 2) You may make style/grammar improvements only if meaning is unchanged. 3) Extract functional requirements (FRs) ONLY from: - the flows in UC-18.md, and - the checks/expectations in UC-18-AT.md Do not add “nice-to-have” requirements that aren’t supported by those sources. 4) Keep implementation constraints: Python, vanilla HTML/CSS/JS. 5) Treat this use case as its own feature branch (branch naming suggestion is fine, but don’t actually run git commands unless asked). Spec contents required: - Feature name (from use case title) - Summary / goal - Actors - Preconditions - Triggers - Main flow (verbatim from use case) - Alternate flows (verbatim) - Exception/error flows (verbatim) - Data involved (only what the use case mentions) - Functional requirements list (numbered FR-01-001, FR-01-015, ...) - Traceability section mapping: - each acceptance test → related FRs - each flow step (or flow section) → related FRs (coarse mapping is fine) Output: - Update/produce the spec.md for this feature. If Spec-Kit expects a per-feature folder/file, follow the tool's convention, but the content must match the above constraints."

## Summary

Enable a maintainer to ingest municipal census datasets, normalize and link them to internal area keys, compute neighbourhood indicators, and publish those indicators safely for valuation and user-facing neighbourhood context.

## Goal

The maintainer ingests municipal census datasets so the system can compute neighbourhood indicators used by the valuation engine and for user-facing context.

## Actors

- **Primary Actor**: Maintainer (Data Engineer / System Operator)
- **Secondary Actors**: Open Data Provider (municipal census portal), Ingestion Pipeline, Database/Feature Store, Boundary Dataset (neighbourhood polygons), Validation/QA Module, Scheduler (optional)

## Preconditions

- Census dataset sources and expected schemas are configured.
- Neighbourhood boundary definitions (or equivalent join keys) exist in the database to support linking census records to areas.
- The database has tables for raw census imports and for computed indicators.

## Trigger

The maintainer starts a census ingestion run or a scheduled job starts the run.

## User Scenarios & Testing

### User Story 1 - Publish validated neighbourhood indicators (Priority: P1)

As a maintainer, I want census datasets ingested, normalized, linked, and transformed into neighbourhood indicators so the valuation engine and UI can use current area-level context.

**Why this priority**: This is the core value of UC-18 and the minimum independently useful outcome.

**Independent Test**: Run census ingestion against valid artifacts and verify that normalized census data and computed indicators are published with run metadata and coverage details.

**Acceptance Scenarios**:

1. **Given** a maintainer starts census ingestion with valid data, **When** the pipeline completes, **Then** the system reports success and computed neighbourhood indicators are available in production.
2. **Given** a successful run, **When** the maintainer inspects metadata, **Then** the system shows provenance, census year, geography level, coverage, counts, and warnings.

### User Story 2 - Block inconsistent indicators from publication (Priority: P2)

As a maintainer, I want schema, value, linking, computation, coverage, and promotion failures to stop publication so inconsistent indicators do not replace the last known-good version.

**Why this priority**: Safe failure handling is required because inconsistent neighbourhood indicators would directly affect valuation and user-facing context.

**Independent Test**: Run negative fixtures for schema changes, invalid values, suppression, key mismatch, computation failure, low coverage, and promotion failure, then verify that promotion is blocked and prior production indicators remain unchanged.

**Acceptance Scenarios**:

1. **Given** validation, linking, or computation problems occur, **When** the pipeline processes the run, **Then** the system reports actionable details and does not publish inconsistent indicators.
2. **Given** coverage or promotion fails, **When** the run reaches QA or publication, **Then** production remains on the last known-good version.

### User Story 3 - Audit and repeat census runs (Priority: P3)

As a maintainer, I want every census ingestion run to be traceable and repeatable so I can audit provenance, compare outputs, and monitor coverage over time.

**Why this priority**: Run-level traceability is required for auditability and operational confidence.

**Independent Test**: Execute repeated runs with unchanged sources and configuration and verify distinct run IDs plus consistent indicator outputs within expected tolerances.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the maintainer reviews the run report, **Then** the system exposes run identifiers, provenance, coverage metrics, QA outcomes, and promotion status.
2. **Given** the same artifacts and configuration are ingested repeatedly, **When** runs complete successfully, **Then** indicator outputs remain consistent within defined tolerances and the version fields remain stable.

### Edge Cases

- Census artifacts can contain suppressed or rounded values that must not be treated as real zeros.
- Geography keys can fail to match internal boundaries, reducing coverage below the required threshold.
- Indicator computation can fail because of division by zero or missing derived prerequisites.
- Promotion can fail because of database errors, locks, or permission issues, and the prior production version must remain intact.

## Main Flow

### Main Success Scenario

1. The maintainer initiates ingestion for the configured municipal census datasets.
2. The system fetches dataset metadata (collection year, geography level, field definitions, refresh date).
3. The system downloads census data artifacts to staging.
4. The system validates the artifacts:
    * file integrity and readability
    * required columns present (e.g., population, household counts, income proxies where available)
    * value constraints (non-negative counts, valid codes)
5. The system normalizes the data to canonical internal schemas:
    * standardizes column names and types
    * handles missing values with explicit nulls and/or sentinel handling
    * maps geographic identifiers to internal area keys (e.g., neighbourhood ID, census tract)
6. The system loads raw normalized census data into staging tables.
7. The system computes neighbourhood indicators from the raw census data (e.g., density, demographic proxies, socioeconomic indicators defined by the project).
8. The system runs QA checks:
    * totals and ranges are within expected bounds
    * indicators are computable for expected areas
    * join coverage checks (percentage of areas with data)
9. The system promotes the new indicator tables to production and records metadata (year/version, coverage, warnings).
10. The system reports success and makes indicators available to the valuation engine and UI.

## Alternate Flows

None.

## Exception/Error Flows

- **4a**: Census artifact contains suppressed/rounded values (privacy rules)
  - 4a1: The system preserves suppressed fields as nulls and computes indicators with documented fallback rules.
  - 4a2: The system flags indicators that rely on suppressed values as “limited accuracy”.
- **5a**: Geographic keys do not match internal boundaries (code changes, new boundaries)
  - 5a1: The system attempts a mapping table lookup (old-to-new codes).
  - 5a2: If mapping is incomplete, the system reports uncovered areas and blocks promotion until resolved.
- **7a**: Indicator computation fails (division by zero, missing required columns)
  - 7a1: The system stops the run, reports which indicators failed and why, and keeps existing production indicators.
- **8a**: Coverage falls below threshold (too many areas missing data)
  - 8a1: The system blocks promotion and reports which areas are missing census data.

## Data Involved

- Configured census dataset sources and expected schemas.
- Dataset metadata including collection year, geography level, field definitions, and refresh date.
- Downloaded census data artifacts in staging.
- Artifact validation results including file integrity, readability, required columns, and value constraints.
- Canonical internal census schemas with standardized column names and types.
- Missing values, null handling, and sentinel handling where applicable.
- Geographic identifiers and internal area keys such as neighbourhood IDs or census tracts.
- Raw normalized census staging tables.
- Computed neighbourhood indicators.
- QA outputs including totals, ranges, indicator computability, and join coverage metrics.
- Production indicator tables and recorded metadata such as year/version, coverage, warnings, and failure details.

## Requirements

### Functional Requirements

- **FR-01-001**: The system MUST allow a maintainer to start a census ingestion run for configured municipal census datasets, either manually or through a scheduled job.
- **FR-01-002**: The system MUST fetch dataset metadata for each census artifact, including collection year, geography level, field definitions, and refresh date.
- **FR-01-003**: The system MUST download census data artifacts to staging before validation and publication proceed.
- **FR-01-004**: The system MUST validate each artifact for integrity, readability, required columns, and value constraints before normalization and promotion can proceed.
- **FR-01-005**: The system MUST normalize census data into canonical internal schemas by standardizing column names and types, handling missing values explicitly, and mapping geographic identifiers to internal area keys.
- **FR-01-006**: The system MUST load raw normalized census data into staging tables before indicator publication proceeds.
- **FR-01-007**: The system MUST compute neighbourhood indicators from the raw census data.
- **FR-01-008**: The system MUST run QA checks that verify totals and ranges, confirm indicators are computable for expected areas, and measure join coverage.
- **FR-01-009**: The system MUST promote new indicator tables to production atomically and record production metadata including year or version, coverage, and warnings.
- **FR-01-010**: The system MUST report success and make published indicators available to the valuation engine and UI after a successful run.
- **FR-01-011**: If census artifacts contain suppressed or rounded values, the system MUST preserve suppressed fields as nulls or equivalent explicit suppression handling, compute indicators using documented fallback rules, and flag affected indicators as limited accuracy or equivalent.
- **FR-01-012**: If geographic keys do not match internal boundaries, the system MUST attempt mapping table lookup and MUST block promotion while reporting uncovered areas when mapping remains incomplete.
- **FR-01-013**: If indicator computation fails, the system MUST stop the run, report which indicators failed and why, and keep existing production indicators unchanged.
- **FR-01-014**: If coverage falls below the configured threshold, the system MUST block promotion and report which areas are missing census data.
- **FR-01-015**: The system MUST record run metadata including run ID, timestamps, census year, geography level, coverage, counts, warnings, QA outcomes, and production status for each ingestion run.
- **FR-01-016**: If validation detects missing required columns, indicator computation and promotion MUST NOT proceed and the last known-good production indicators MUST remain unchanged.
- **FR-01-017**: If validation detects invalid counts, invalid codes, or null required keys, the system MUST fail the run or quarantine invalid records according to configured policy, report counts and reasons, and MUST NOT promote inconsistent indicators.
- **FR-01-018**: The system MUST represent missing values explicitly using nulls or configured sentinel strategy and MUST ensure required keys are populated for retained records or invalid records are quarantined with reporting.
- **FR-01-019**: The system MUST record coverage metrics for geography linking and pass the run only when coverage meets the configured threshold.
- **FR-01-020**: Computed indicators for covered areas MUST satisfy basic configured constraints such as non-negative densities and valid percentage ranges where applicable.
- **FR-01-021**: If promotion fails, the system MUST report actionable database error details, keep production indicator tables or views on the last known-good version, and MUST NOT record the run as a successful production version.
- **FR-01-022**: When scheduler-based ingestion is enabled, scheduled runs MUST produce the same run metadata, coverage, and QA outcome reporting behavior as manual runs.
- **FR-01-023**: Repeated ingestion runs against the same artifacts and configuration MUST produce consistent indicator outputs within defined tolerances or rounding rules while recording distinct run IDs and timestamps with the same census year or version fields.

### Non-Functional Requirements

- **NFR-01**: Ingestion and indicator computation MUST complete within the agreed operational window for target dataset sizes.
- **NFR-02**: Download, validation, linking, computation, QA, and promotion failures MUST be detected and reported without corrupting production indicators.
- **NFR-03**: Every census ingestion run MUST be auditable through recorded run IDs, provenance, coverage metrics, warnings, QA outcomes, and promotion status.

### Key Entities

- **Census Ingestion Run**: A single manual or scheduled census ingestion attempt with its identifiers, timing, coverage, warnings, and outcomes.
- **Census Artifact**: A source census dataset together with its metadata, contents, and validation status.
- **Area Link**: The mapping between source census geography identifiers and internal area keys used for indicator publication.
- **Neighbourhood Indicator Set**: The computed indicator records published for internal areas after successful validation, linking, QA, and promotion.

## Success Criteria

### Measurable Outcomes

- **SC-01**: In 100% of successful census ingestion runs, computed neighbourhood indicators are available in production and the run metadata records run ID, timestamps, census year, geography level, coverage, and warnings.
- **SC-02**: In 100% of schema, invalid-value, linking, computation, coverage, and promotion failure test cases, inconsistent indicators are not promoted and the last known-good production version remains unchanged.
- **SC-03**: In 100% of successful runs, the maintainer can inspect provenance and versioning details including census year, refresh or publish date when available, geography level, source or provider information, and boundary vintage when applicable.
- **SC-04**: For repeated runs against unchanged sources and configuration, indicator outputs remain consistent within defined tolerances while each run records distinct run IDs and timestamps.

## Assumptions

- The scenario file was used only to clarify terminology and operational context; the use case and acceptance tests remain the source of truth.
- Exact indicator definitions, allowed formulas, and thresholds are configuration-driven and not expanded beyond the source files in this spec.

## Traceability

### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-18-01 | FR-01-001, FR-01-006, FR-01-007, FR-01-009, FR-01-010, FR-01-015 |
| AT-18-02 | FR-01-002, FR-01-015 |
| AT-18-03 | FR-01-004, FR-01-016 |
| AT-18-04 | FR-01-004, FR-01-017 |
| AT-18-05 | FR-01-005, FR-01-018 |
| AT-18-06 | FR-01-005, FR-01-015, FR-01-019 |
| AT-18-07 | FR-01-012, FR-01-019 |
| AT-18-08 | FR-01-011 |
| AT-18-09 | FR-01-007, FR-01-020 |
| AT-18-10 | FR-01-013 |
| AT-18-11 | FR-01-014, FR-01-019 |
| AT-18-12 | FR-01-009, FR-01-015 |
| AT-18-13 | FR-01-021 |
| AT-18-14 | FR-01-001, FR-01-015, FR-01-022 |
| AT-18-15 | FR-01-015, FR-01-023 |

### Flow Steps and Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow 1 | FR-01-001 |
| Main Flow 2 | FR-01-002 |
| Main Flow 3 | FR-01-003 |
| Main Flow 4 | FR-01-004 |
| Main Flow 5 | FR-01-005 |
| Main Flow 6 | FR-01-006 |
| Main Flow 7 | FR-01-007 |
| Main Flow 8 | FR-01-008, FR-01-019 |
| Main Flow 9 | FR-01-009, FR-01-015 |
| Main Flow 10 | FR-01-010 |
| Exception Flow 4a | FR-01-011 |
| Exception Flow 5a | FR-01-012 |
| Exception Flow 7a | FR-01-013 |
| Exception Flow 8a | FR-01-014 |
