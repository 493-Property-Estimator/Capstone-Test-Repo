# Feature Specification: Ingest property tax assessment data

**Feature Branch**: `019-ingest-tax-assessments`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description derived from `Use Cases/UC-19.md`, `Scenarios/UC-19-Scenarios.md`, and `Acceptance Tests/UC-19-AT.md`

## Summary / Goal

Enable the maintainer to ingest a new property tax assessment dataset so the valuation system can maintain a versioned, queryable assessment baseline that valuation requests can use as their starting point.

## Clarifications

### Session 2026-03-10

- Q: What is the invalid assessment record handling policy for UC-19? → A: Quarantine invalid rows, continue processing valid rows, and block promotion only if invalid-rate QA exceeds threshold.
- Q: What duplicate-resolution precedence applies when multiple records map to one canonical location ID? → A: Prefer highest confidence match first, then latest year only when duplicates span multiple years.

## Actors

- **Primary Actor**: Maintainer (Data Engineer / System Operator)
- **Secondary Actors**: Open Data Provider (assessment dataset), Ingestion Pipeline, Database/Assessment Store, Validation/QA Module, Geospatial Linking (parcels/addresses), Scheduler (optional)

## Preconditions

- Assessment dataset source and expected schema are configured.
- A canonical location strategy exists (e.g., parcel ID, address key, or spatial join to parcel polygons).
- Database schemas exist for raw assessment records, normalized records, and lookup indexes.

## Triggers

- A new assessment dataset release is available.
- A scheduled refresh run begins.

## Assumptions

- A known last known-good production baseline exists before any negative-path validation, QA, or promotion-failure run.
- Deterministic rules exist for resolving ambiguous links and duplicate mappings when the source data creates multiple candidates.
- Configured QA thresholds exist for ambiguity, linking coverage, abnormal coverage change, and outlier tolerance.

## Dependencies

- Availability of the assessment dataset from the configured source/provider
- Availability of canonical location identifiers and parcel, address, or spatial linking inputs needed to connect assessment records to system locations
- Availability of production and staging baseline storage needed to preserve the last known-good baseline during failed runs

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish assessment baseline (Priority: P1)

As a maintainer, I need to run an assessment-data ingestion process that produces a new production baseline so valuation requests can use updated assessment values.

**Why this priority**: This is the core business outcome of UC-19. Without a successful ingest and promotion, the feature provides no usable baseline.

**Independent Test**: Can be fully tested by running ingestion on a valid dataset and confirming the new baseline is queryable by canonical location ID with recorded run metadata.

**Acceptance Scenarios**:

1. **Given** a valid assessment dataset, **When** the maintainer initiates ingestion and the pipeline completes, **Then** the system reports success, publishes a queryable baseline, and records run metadata. (`AT-19-01`)
2. **Given** a successful run, **When** the maintainer reviews run metadata, **Then** provenance, year/version details, timestamps, and counts are visible. (`AT-19-02`)
3. **Given** a successful staging run, **When** promotion occurs, **Then** the new baseline is promoted atomically without exposing a partial state. (`AT-19-10`)

---

### User Story 2 - Prevent unsafe publication (Priority: P1)

As a maintainer, I need the system to stop bad, incomplete, or poor-quality assessment data from reaching production so the existing baseline remains trustworthy.

**Why this priority**: Protecting the last known-good baseline is as critical as a successful ingest because downstream valuation depends on production integrity.

**Independent Test**: Can be fully tested by running ingestion against invalid schema, invalid values, low-coverage data, extreme outliers, and forced promotion failures, then confirming production remains unchanged.

**Acceptance Scenarios**:

1. **Given** required fields are missing or renamed, **When** schema validation runs, **Then** the run fails with actionable details and downstream stages do not proceed. (`AT-19-03`)
2. **Given** invalid assessment values or missing required keys, **When** validation and normalization run, **Then** invalid data is rejected or quarantined according to policy and not silently converted into misleading values. (`AT-19-04`)
3. **Given** linking coverage or outlier rates violate QA thresholds, **When** QA runs, **Then** promotion is blocked and the prior production baseline remains intact. (`AT-19-07`, `AT-19-09`)
4. **Given** promotion fails after staging passes QA, **When** the system attempts promotion, **Then** the system reports the failure and preserves the last known-good production baseline. (`AT-19-11`)

---

### User Story 3 - Produce auditable, repeatable linking outcomes (Priority: P2)

As a maintainer, I need linking, duplicate handling, and repeat runs to behave deterministically so baseline results are auditable and consistent.

**Why this priority**: Deterministic linking and duplicate resolution are essential for trust, auditability, and repeatability, but they build on the successful ingest flow.

**Independent Test**: Can be fully tested by running datasets with ambiguous links, duplicate mappings, scheduled execution, and repeated fixed-input runs, then comparing the resulting metrics and linked outputs.

**Acceptance Scenarios**:

1. **Given** a valid or ambiguous dataset, **When** linking runs, **Then** each retained record is linked or marked unlinked with metrics recorded, and ambiguity is resolved deterministically with audit flags. (`AT-19-05`, `AT-19-06`)
2. **Given** duplicate mappings to one canonical location ID, **When** duplicates are detected, **Then** deterministic resolution rules are applied and conflicting production baseline values are prevented. (`AT-19-08`)
3. **Given** a scheduled run or repeated runs with fixed inputs, **When** ingestion completes, **Then** metadata remains consistent with manual runs and deterministic outcomes remain stable across runs. (`AT-19-12`, `AT-19-13`)

### Edge Cases

- Assessment schema changes after the source is configured.
- Downloaded assessment files fail integrity checks.
- Records contain non-numeric, negative, or missing assessment values.
- Records cannot be linked to canonical location IDs or produce ambiguous matches.
- Multiple assessment rows map to the same canonical location ID.
- Invalid-record rates exceed the configured QA threshold after quarantining.
- QA detects abnormal coverage drops or excessive outlier rates.
- Promotion fails after staging has passed validation, linking, and QA.

## Use Case Flows

### Main Flow (verbatim from use case)

1. The maintainer initiates ingestion for property tax assessment data (or a scheduled job starts it).
2. The system fetches dataset metadata (assessment year, publication date, coverage notes, license).
3. The system downloads the assessment dataset to staging and validates file integrity.
4. The system validates the dataset schema and key fields (e.g., assessment value, property identifier/address, location fields).
5. The system normalizes assessment records:
   - standardizes types and units (currency, numeric fields)
   - normalizes address formats and/or parcel identifiers
   - handles missing/invalid entries according to rules (drop, quarantine, or null)
6. The system links each assessment record to the system’s canonical location ID:
   - direct match via parcel identifier/address key when available
   - spatial join to parcels/boundaries if geometry is provided or derivable
7. The system loads normalized and linked records into staging tables and builds lookup indexes for fast retrieval (by canonical location ID).
8. The system runs QA checks:
   - coverage: percentage of locations with assessment values
   - outliers: extremely high/low values flagged for review
   - duplicates: multiple records mapping to the same canonical location handled per rule (latest year, highest confidence match)
9. The system promotes the new assessment baseline tables to production and records versioning metadata (year, run ID, counts, warnings).
10. The system reports success; valuation requests can now anchor estimates to the new baseline.

### Alternate Flows (verbatim from use case extensions)

- **4a**: Assessment schema changes (field renamed/removed)
  - **4a2**: The maintainer updates schema mappings and re-runs.
- **6a**: Linking ambiguity (multiple candidate parcels/addresses)
  - **6a1**: The system selects a best match using a deterministic confidence rule and flags ambiguous links for audit.

### Exception / Error Flows (verbatim from use case extensions)

- **4a**: Assessment schema changes (field renamed/removed)
  - **4a1**: The system fails the run for assessment ingestion and reports missing/changed fields.
- **6a**: Linking ambiguity (multiple candidate parcels/addresses)
  - **6a2**: If ambiguity exceeds a threshold, the system blocks promotion and reports problematic records.
- **8a**: QA detects abnormal coverage drop compared to previous year/version
  - **8a1**: The system blocks promotion and reports coverage deltas and affected regions.
- **9a**: Promotion fails
  - **9a1**: The system rolls back changes and preserves the existing production baseline.

## Requirements *(mandatory)*

### Feature Details

#### Data Involved

- Assessment dataset metadata: assessment year, publication date, coverage notes, license, source/provider information when available
- Assessment records: assessment value, property identifier/address, location fields, parcel identifiers, geometry when provided or derivable
- Canonical location ID used to link and retrieve baseline values
- Staging data for raw, normalized, and linked assessment records
- Lookup indexes for retrieval by canonical location ID
- QA outputs: coverage metrics, unlinked metrics, ambiguous-link metrics, duplicate metrics, outlier warnings, affected regions
- Run metadata: run ID, start and end timestamps, counts, warnings, promotion status
- Production baseline version metadata keyed by assessment year and run ID

#### Implementation Constraints

- The feature implementation must remain within Python and vanilla HTML/CSS/JS project constraints.

### Functional Requirements

- **FR-01-001**: The system MUST allow the maintainer to initiate assessment ingestion manually, and it MUST support scheduler-initiated runs when scheduling is enabled.
- **FR-01-002**: The system MUST fetch and record dataset metadata for each run, including assessment year, publication or refresh date when available, coverage notes, and license or source/provider information when available.
- **FR-01-003**: The system MUST download the assessment dataset into staging and validate file integrity before schema validation, linking, QA, or promotion proceeds.
- **FR-01-004**: The system MUST validate the dataset schema and required key fields, and if required fields are missing or changed it MUST fail the run with actionable details and stop loading, linking, and promotion.
- **FR-01-005**: The system MUST normalize assessment records by standardizing types and units, normalizing addresses and/or parcel identifiers, and handling missing or invalid entries according to defined rules.
- **FR-01-006**: The system MUST quarantine invalid records while continuing to process valid records, report counts and reasons for quarantined records, and MUST NOT silently coerce invalid assessment values into misleading numeric values.
- **FR-01-007**: The system MUST link each retained assessment record to the system's canonical location ID using configured direct-match keys and spatial joins when geometry is provided or derivable, or mark the record unlinked with a reason code.
- **FR-01-008**: The system MUST resolve ambiguous candidate matches by deterministic tie-break rules, flag ambiguous links for audit, and record the link method and confidence indicator for those records.
- **FR-01-009**: The system MUST load normalized and linked records into staging tables and build or update lookup indexes required for fast retrieval by canonical location ID.
- **FR-01-010**: The system MUST compute and record QA and linking metrics for each run, including linked, unlinked, and ambiguous percentages, duplicate rate and resolution outcomes, outlier counts, and coverage measures.
- **FR-01-011**: The system MUST block promotion when ambiguity, invalid-record rate, linking coverage, abnormal coverage drop, or outlier conditions exceed configured QA thresholds, and it MUST preserve the last known-good production baseline when promotion is blocked.
- **FR-01-012**: The system MUST resolve duplicate mappings to the same canonical location ID by preferring the highest-confidence match first and using the latest year only when duplicates span multiple years, and it MUST prevent conflicting multiple production baseline values for the same canonical location ID unless those values are explicitly versioned and queryable.
- **FR-01-013**: The system MUST promote a successful assessment baseline atomically so production lookups never observe a partially promoted state.
- **FR-01-014**: If promotion fails, the system MUST report actionable failure details, roll back or preserve the existing production baseline, and MUST NOT record the run as a successful production baseline version.
- **FR-01-015**: The system MUST record run metadata and provenance for each run, including run ID, assessment year, start and end timestamps, raw, normalized, linked, and unlinked counts, warnings, QA outcomes, and promotion status.
- **FR-01-016**: After a successful promotion, the system MUST make the assessment baseline queryable in production by canonical location ID so valuation requests can use the new baseline.
- **FR-01-017**: Scheduled runs, when enabled, MUST produce the same categories of run metadata and QA outcomes as manual runs, and success or failure MUST be emitted to monitoring or alerts according to configuration.
- **FR-01-018**: Repeated runs with the same inputs and configuration MUST produce consistent linking coverage, duplicate resolution outcomes, and baseline values for a fixed assessment year within the applicable rounding rules or tolerances, while still recording distinct run IDs and timestamps.

### Non-Functional Requirements

- **NFR-001**: Ingestion, linking, and index build must complete within an agreed operational window for target dataset sizes.
- **NFR-002**: Failures in download, validation, linking, QA, or promotion must be detected and reported without corrupting production data.
- **NFR-003**: Every run must be auditable by run ID and retain provenance, linking outcomes, QA results, warnings, and promotion status.

### Key Entities *(include if feature involves data)*

- **Assessment Dataset**: The source artifact and its metadata for a specific assessment year and publication cycle.
- **Assessment Record**: A single normalized property assessment entry containing value, identifiers, location data, and link status.
- **Canonical Location**: The system-owned location identifier to which assessment records are linked for valuation lookups.
- **Run Metadata**: The audit record for one ingestion execution, including counts, timestamps, QA outcomes, warnings, and promotion status.
- **Production Baseline Version**: The promoted assessment baseline associated with a run ID and assessment year.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-19-01 | FR-01-001, FR-01-002, FR-01-003, FR-01-009, FR-01-013, FR-01-015, FR-01-016 |
| AT-19-02 | FR-01-002, FR-01-015 |
| AT-19-03 | FR-01-004, FR-01-011 |
| AT-19-04 | FR-01-005, FR-01-006 |
| AT-19-05 | FR-01-007, FR-01-010, FR-01-015 |
| AT-19-06 | FR-01-008, FR-01-010, FR-01-011 |
| AT-19-07 | FR-01-010, FR-01-011 |
| AT-19-08 | FR-01-010, FR-01-012 |
| AT-19-09 | FR-01-010, FR-01-011, FR-01-015 |
| AT-19-10 | FR-01-013, FR-01-015, FR-01-016 |
| AT-19-11 | FR-01-014 |
| AT-19-12 | FR-01-001, FR-01-017 |
| AT-19-13 | FR-01-008, FR-01-012, FR-01-018 |

#### Flow Steps to Functional Requirements

| Flow Step / Section | Related FRs |
| --- | --- |
| Main Flow 1 | FR-01-001 |
| Main Flow 2 | FR-01-002 |
| Main Flow 3 | FR-01-003 |
| Main Flow 4 | FR-01-004 |
| Main Flow 5 | FR-01-005, FR-01-006 |
| Main Flow 6 | FR-01-007, FR-01-008 |
| Main Flow 7 | FR-01-009 |
| Main Flow 8 | FR-01-010, FR-01-011, FR-01-012 |
| Main Flow 9 | FR-01-013, FR-01-014, FR-01-015 |
| Main Flow 10 | FR-01-016 |
| Alternate Flows 4a / 6a | FR-01-004, FR-01-008 |
| Exception / Error Flows 4a / 6a / 8a / 9a | FR-01-004, FR-01-011, FR-01-014 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid assessment-ingestion runs produce a production-queryable baseline for the target assessment year.
- **SC-002**: 100% of failed schema-validation, QA-threshold, and promotion-failure test runs leave the last known-good production baseline unchanged.
- **SC-003**: 100% of successful runs produce inspectable provenance and run metadata containing the required year, source, timestamp, count, QA, and promotion details.
- **SC-004**: 100% of repeated runs against the same input and configuration produce consistent linking coverage, duplicate-resolution outcomes, and fixed-year baseline values within defined tolerances.
