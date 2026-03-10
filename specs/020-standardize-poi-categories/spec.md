# Feature Specification: Standardize POI categories across sources

**Feature Branch**: `020-standardize-poi-categories`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description derived from `Use Cases/UC-20.md`, `Scenarios/UC-20-Scenarios.md`, and `Acceptance Tests/UC-20-AT.md`

## Summary / Goal

Enable the maintainer to standardize POI categories from multiple sources into a canonical taxonomy so downstream feature computation can use consistent, comparable amenity semantics across sources.

## Clarifications

### Session 2026-03-10

- Q: How should conflict detection treat the same raw label across sources? → A: A raw label must map consistently within each source; the same label may map differently in different sources.
- Q: Can permissive governance allow promotion when mapping conflicts exist? → A: Conflicts always block promotion; permissive governance applies only to unmapped-threshold handling.

## Actors

- **Primary Actor**: Maintainer (Data Steward / Data Engineer)
- **Secondary Actors**: Category Taxonomy (mapping rules), Ingestion Pipeline, Database/Feature Store, Upstream POI Sources

## Preconditions

- A canonical POI taxonomy exists (e.g., "School", "Park", "Hospital", "Grocery", "Transit", etc.).
- A mapping mechanism exists (lookup table, rules engine, or configuration) for translating source-specific categories into canonical categories.
- POI ingestion stores raw source category fields to allow reclassification without re-downloading.

## Triggers

- A new POI dataset is ingested.
- A new source is added.
- The maintainer updates the category taxonomy.

## Assumptions

- Governance policy is configured to either block promotion or allow promotion with warnings when unmapped labels or conflicts exceed thresholds.
- Taxonomy and mapping versions are identifiable for each standardization run.
- A known last known-good standardized production version exists before negative-path QA or promotion-failure runs.

## Dependencies

- Availability of ingested raw POIs and their source category fields
- Availability of the canonical taxonomy and mapping rules used for standardization
- Availability of staging and production storage that supports safe publication of standardized categories

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish standardized categories (Priority: P1)

As a maintainer, I need a POI category standardization run to assign canonical categories across sources so downstream feature computation can use one consistent category system.

**Why this priority**: This is the core business outcome of UC-20. Without standardized production categories, downstream consumers still depend on inconsistent source labels.

**Independent Test**: Can be fully tested by running standardization on multi-source POIs with complete mappings and confirming canonical categories, provenance, and version metadata are published successfully.

**Acceptance Scenarios**:

1. **Given** raw POIs and configured taxonomy and mapping rules, **When** the maintainer runs standardization, **Then** each standardized POI receives a canonical category and the run records run ID plus taxonomy and mapping versions. (`AT-20-01`)
2. **Given** a successful run, **When** a standardized POI record is inspected, **Then** raw categories, canonical categories, mapping metadata, and provenance remain visible together. (`AT-20-02`)
3. **Given** a successful staging run, **When** promotion occurs, **Then** standardized categories become visible atomically and downstream feature computation can query canonical categories consistently across sources. (`AT-20-10`, `AT-20-12`)

---

### User Story 2 - Enforce mapping governance (Priority: P1)

As a maintainer, I need mapping quality and governance thresholds enforced so incomplete or conflicting categorization does not silently degrade production semantics.

**Why this priority**: Mapping quality directly affects downstream feature correctness, so unsafe or low-quality standardization must be surfaced and governed before publication.

**Independent Test**: Can be fully tested by running standardization with new labels, conflicting mappings, threshold breaches, and forced promotion failures, then verifying the system either blocks or warns according to governance policy.

**Acceptance Scenarios**:

1. **Given** a standardization run on staging, **When** QA executes, **Then** mapped, unmapped, and conflict metrics are computed and reported. (`AT-20-04`)
2. **Given** new raw labels or excessive unmapped rates, **When** standardization and QA run, **Then** affected POIs are marked as unmapped and promotion behavior follows configured governance policy. (`AT-20-05`, `AT-20-08`)
3. **Given** conflicting mappings under strict governance or a promotion failure after QA passes, **When** the system evaluates or promotes the run, **Then** promotion is blocked or rolled back and the last known-good production version remains unchanged. (`AT-20-07`, `AT-20-11`)

---

### User Story 3 - Support deterministic and repeatable reclassification (Priority: P2)

As a maintainer, I need standardization to be deterministic and rerunnable from stored raw categories so taxonomy changes do not require re-ingesting source data.

**Why this priority**: Deterministic assignments and reclassification are essential for auditability and controlled taxonomy evolution, but they build on the core publish-and-govern flow.

**Independent Test**: Can be fully tested by re-running the same inputs with fixed taxonomy and mapping versions, then re-running after a taxonomy change and comparing assignments and metadata.

**Acceptance Scenarios**:

1. **Given** identical inputs and identical taxonomy and mapping versions, **When** standardization is run multiple times, **Then** the same POIs receive identical canonical assignments while run IDs and timestamps remain unique. (`AT-20-03`)
2. **Given** multi-field source categories, **When** standardization runs, **Then** precedence rules are applied and the selected raw fields and rationale are auditable. (`AT-20-06`)
3. **Given** a taxonomy change, **When** the maintainer reruns standardization, **Then** canonical categories update from stored raw POIs without re-downloading source data. (`AT-20-09`)

### Edge Cases

- New or unrecognized raw category labels appear in a source.
- The same raw label maps to multiple canonical categories.
- A source provides multiple category fields that require precedence rules.
- Unmapped or conflict rates exceed governance thresholds.
- A taxonomy change requires reclassification from stored raw POIs.
- Promotion fails after staging passes standardization and QA.

## Use Case Flows

### Main Flow (verbatim from use case)

1. The maintainer defines or reviews the canonical POI taxonomy used by the valuation system.
2. The system ingests POIs from one or more open-data sources (UC-17) and stores raw category fields.
3. The system applies mapping rules to each POI to assign a canonical category (and optional subcategory).
4. The system records both the raw source category and the canonical category for traceability.
5. The system validates mapping quality:
   - percentage mapped vs unmapped
   - detection of conflicting mappings (same raw label mapped to multiple canonical categories)
6. The system loads standardized POIs into production tables used for feature computation.
7. The system reports mapping results to the maintainer and highlights unmapped labels for taxonomy updates.

### Alternate Flows (verbatim from use case extensions)

- **3a**: New/unrecognized source categories appear
  - **3a1**: The system assigns "Unmapped/Other" and records the raw label.
  - **3a2**: The system generates a report of unmapped labels and counts for the maintainer to classify.
- **3b**: A source provides multiple category fields (e.g., type + subtype)
  - **3b1**: The system applies precedence rules (prefer subtype when present) and records the chosen rationale.
- **6a**: A canonical taxonomy change occurs (reclassification)
  - **6a1**: The system reprocesses stored raw POIs to update canonical categories without re-downloading source data.

### Exception / Error Flows (verbatim from use case extensions)

- **5a**: Mapping quality below threshold (too many unmapped POIs)
  - **5a1**: The system blocks promotion or promotes with warnings based on governance policy.
  - **5a2**: The maintainer updates mapping rules and reruns standardization.

## Requirements *(mandatory)*

### Feature Details

#### Data Involved

- Canonical POI taxonomy, including canonical categories and optional subcategories
- Raw POI category fields captured from one or more open-data sources
- Canonical category assignments and optional subcategory assignments for each POI
- Raw source category values stored alongside canonical category values for traceability
- Mapping rules and precedence rules used to translate source-specific categories
- Mapping quality outputs: mapped percentage, unmapped percentage, conflicting mappings, unmapped labels and counts
- Run metadata: run ID, taxonomy version, mapping version, timestamps, warnings, promotion status

#### Implementation Constraints

- The feature implementation must remain within Python and vanilla HTML/CSS/JS project constraints.

### Functional Requirements

- **FR-01-001**: The system MUST allow the maintainer to define or review the canonical POI taxonomy used for valuation-system category standardization.
- **FR-01-002**: The system MUST ingest or access POIs from one or more open-data sources and store raw category fields for each POI.
- **FR-01-003**: The system MUST apply mapping rules to each POI to assign a canonical category and an optional subcategory when used.
- **FR-01-004**: The system MUST store raw source category values alongside canonical category assignments for traceability.
- **FR-01-005**: The system MUST validate mapping quality by computing mapped versus unmapped percentages and detecting conflicts where the same raw label maps to multiple canonical categories within the same source.
- **FR-01-006**: The system MUST load standardized POIs into production data used for downstream feature computation when publication is allowed by governance policy.
- **FR-01-007**: The system MUST report mapping results to the maintainer, including unmapped labels that require taxonomy updates.
- **FR-01-008**: When new or unrecognized source categories appear, the system MUST assign `Unmapped/Other` or an equivalent unmapped category, record the raw label, and report unmapped labels with counts.
- **FR-01-009**: When a source provides multiple category fields, the system MUST apply precedence rules and record the rationale for the chosen field or mapping outcome.
- **FR-01-010**: The system MUST enforce the configured governance policy when unmapped rates fall below threshold by either blocking promotion or promoting with explicit warnings and unmapped flags per POI, and it MUST state the applied policy in the run report.
- **FR-01-011**: The system MUST support rerunning standardization after mapping-rule updates so the maintainer can rerun standardization after threshold failures.
- **FR-01-012**: When the canonical taxonomy changes, the system MUST reprocess stored raw POIs to update canonical categories without re-downloading source data.
- **FR-01-013**: The system MUST record run metadata for each run, including run ID and taxonomy and mapping version identifiers.
- **FR-01-014**: The system MUST produce deterministic canonical category assignments for the same POIs when the inputs and taxonomy and mapping versions are unchanged.
- **FR-01-015**: The system MUST retain source provenance fields and raw category fields in standardized output records.
- **FR-01-016**: The system MUST include mapping metadata for standardized POIs sufficient to identify the rule or rationale used for the category assignment.
- **FR-01-017**: The system MUST report mapping quality outputs for each run, including mapped percentage, unmapped percentage, conflicts, conflicting labels with their competing canonical mappings within a source when present, and unmapped labels with counts by source when present.
- **FR-01-018**: The system MUST block promotion when conflicts exceed threshold and preserve the last known-good production standardized categories, regardless of whether the configured governance policy is strict or permissive for unmapped-threshold handling.
- **FR-01-019**: When promotion is allowed, the system MUST publish standardized categories atomically so downstream readers never observe a partially standardized state.
- **FR-01-020**: If promotion fails, the system MUST report actionable failure details, preserve the last known-good production standardized categories, and MUST NOT record the run as a successful production standardization version.
- **FR-01-021**: After successful promotion, the system MUST make standardized categories usable for downstream queries by canonical category across sources without requiring interpretation of source-specific raw labels.

### Non-Functional Requirements

- **NFR-001**: Standardization must complete within an agreed operational window for target POI volumes.
- **NFR-002**: Mapping-QA and promotion failures must not corrupt production data and must provide actionable diagnostics.
- **NFR-003**: Each run must be auditable by run ID and retain taxonomy and mapping versions, quality metrics, conflicts, warnings, and promotion status.

### Key Entities *(include if feature involves data)*

- **Canonical Taxonomy**: The authoritative set of POI categories and optional subcategories used by downstream feature computation.
- **Raw POI Record**: An ingested POI carrying provenance and one or more raw source category fields.
- **Standardized POI Record**: A POI record with raw category values, canonical category assignments, and mapping metadata.
- **Mapping Rule Set**: The configured translation and precedence logic that maps raw categories to canonical categories.
- **Standardization Run Metadata**: The audit record for one standardization execution, including versions, quality outputs, warnings, and promotion status.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-20-01 | FR-01-002, FR-01-003, FR-01-013, FR-01-015 |
| AT-20-02 | FR-01-004, FR-01-015, FR-01-016 |
| AT-20-03 | FR-01-013, FR-01-014 |
| AT-20-04 | FR-01-005, FR-01-017 |
| AT-20-05 | FR-01-007, FR-01-008, FR-01-017 |
| AT-20-06 | FR-01-009, FR-01-016 |
| AT-20-07 | FR-01-005, FR-01-010, FR-01-018 |
| AT-20-08 | FR-01-010, FR-01-017 |
| AT-20-09 | FR-01-012, FR-01-013 |
| AT-20-10 | FR-01-019 |
| AT-20-11 | FR-01-020 |
| AT-20-12 | FR-01-006, FR-01-021 |

#### Flow Steps to Functional Requirements

| Flow Step / Section | Related FRs |
| --- | --- |
| Main Flow 1 | FR-01-001 |
| Main Flow 2 | FR-01-002 |
| Main Flow 3 | FR-01-003 |
| Main Flow 4 | FR-01-004 |
| Main Flow 5 | FR-01-005, FR-01-010, FR-01-017, FR-01-018 |
| Main Flow 6 | FR-01-006, FR-01-019, FR-01-021 |
| Main Flow 7 | FR-01-007 |
| Alternate Flows 3a / 3b / 6a | FR-01-008, FR-01-009, FR-01-012 |
| Exception / Error Flow 5a | FR-01-010, FR-01-011 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid standardization runs produce canonical category assignments for the targeted POIs and publish them when governance allows promotion.
- **SC-002**: 100% of runs with threshold breaches or promotion failures preserve the last known-good production standardized categories.
- **SC-003**: 100% of successful runs produce inspectable run metadata containing run ID plus taxonomy and mapping version identifiers and mapping-quality outputs.
- **SC-004**: 100% of repeated runs with identical POIs and identical taxonomy and mapping versions produce identical canonical category assignments.
