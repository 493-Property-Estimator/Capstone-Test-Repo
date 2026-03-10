# Feature Specification: Deduplicate open-data entities

**Feature Branch**: `021-deduplicate-open-data`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description derived from `Use Cases/UC-21.md`, `Scenarios/UC-21-Scenarios.md`, and `Acceptance Tests/UC-21-AT.md`

## Summary / Goal

Enable the maintainer to deduplicate open-data entities across sources into canonical entities so downstream computations do not double-count the same real-world amenity or signal.

## Clarifications

### Session 2026-03-10

- Q: How should medium- and low-confidence matches be handled in review behavior? → A: Medium-confidence candidates go to review; low-confidence candidates are rejected and not reviewed by default.
- Q: What precedence order should resolve conflicting source attributes? → A: Prefer the configured preferred source first, then highest quality, then most recent update.

## Actors

- **Primary Actor**: Maintainer (Data Engineer / Data Steward)
- **Secondary Actors**: Ingestion Pipeline, Deduplication/Entity Resolution Module, Spatial Database/Feature Store, Upstream POI/Boundary Sources

## Preconditions

- Multiple open-data sources are ingested and stored with provenance (source, source ID).
- A deduplication strategy is defined (spatial proximity thresholds, name similarity, category matching, stable IDs).
- The system can represent "canonical entity" vs "source-specific records" (e.g., a canonical table with links to source rows).

## Triggers

- A new dataset ingestion occurs.
- The maintainer initiates a deduplication run after adding a new source.

## Assumptions

- Deduplication configuration is fixed per run so candidate generation, scoring, and merge outcomes are deterministic for the same inputs.
- A known last known-good production canonical-entity version exists before negative-path QA or publication-failure runs.
- Publication updates canonical entities and canonical-to-source links together as one production version.

## Dependencies

- Availability of ingested multi-source entities with provenance and geometry or coordinates
- Availability of canonical categories or configured category compatibility rules used during matching
- Availability of staging and production storage for canonical entities, link tables, and review candidates

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish canonical entities (Priority: P1)

As a maintainer, I need deduplication to merge duplicate source records into canonical entities so downstream feature computation counts each real-world place once.

**Why this priority**: This is the primary value of UC-21. Without canonical entities and source links, downstream consumers still double-count overlapping records from different sources.

**Independent Test**: Can be fully tested by running deduplication on overlapping multi-source entities and confirming canonical entities, canonical-to-source links, run metadata, and downstream single-count behavior.

**Acceptance Scenarios**:

1. **Given** ingested multi-source POIs with provenance and geometry, **When** the maintainer runs deduplication, **Then** the system produces canonical entities, canonical-to-source links, and a run report with counts and configuration identifiers. (`AT-21-01`)
2. **Given** a run that passes QA, **When** publication occurs, **Then** canonical entities and link tables become visible atomically under one production version. (`AT-21-10`)
3. **Given** successfully published canonical entities, **When** downstream queries count amenities by canonical category, **Then** the same real-world place contributes only once. (`AT-21-12`)

---

### User Story 2 - Prevent unsafe merges (Priority: P1)

As a maintainer, I need candidate generation, confidence thresholds, and QA safeguards to prevent distinct entities from being merged incorrectly.

**Why this priority**: Incorrect merges are as harmful as missed merges because they distort downstream signals. Over-merge protection is central to acceptable deduplication quality.

**Independent Test**: Can be fully tested by running datasets with close-but-distinct entities, incompatible categories, suspicious cluster behavior, and publication failures, then verifying that unsafe merges do not reach production.

**Acceptance Scenarios**:

1. **Given** candidate-generation test patterns, **When** matching and scoring run, **Then** distance, name, category, and stable-ID evidence are applied and thresholded into auto-merge, review, or reject outcomes. (`AT-21-02`, `AT-21-03`)
2. **Given** close-but-distinct entities or incompatible categories, **When** deduplication runs, **Then** those entities are not auto-merged and only review-eligible cases enter the review list. (`AT-21-05`, `AT-21-06`)
3. **Given** suspicious over-merge signals or a publication failure, **When** QA or publication runs, **Then** publication is blocked or rolled back and production remains on the last known-good version. (`AT-21-09`, `AT-21-11`)

---

### User Story 3 - Keep merge decisions auditable and repeatable (Priority: P2)

As a maintainer, I need deduplication decisions to be deterministic and auditable so merge behavior can be trusted, explained, and rerun consistently.

**Why this priority**: Determinism, precedence rules, and preserved provenance are necessary for governance and operational debugging, but they build on the core deduplication flow.

**Independent Test**: Can be fully tested by repeating the same run configuration, checking stable-ID-driven merges, and inspecting how conflicting source attributes are resolved and preserved.

**Acceptance Scenarios**:

1. **Given** the same inputs and configuration, **When** deduplication is run multiple times, **Then** the same source records map to the same canonical entities while run IDs and timestamps remain unique. (`AT-21-04`)
2. **Given** shared stable identifiers or conflicting source attributes, **When** canonical entities are constructed, **Then** merge rationale and precedence rules are applied and remain auditable. (`AT-21-07`, `AT-21-08`)

### Edge Cases

- Two entities are spatially close but represent distinct real-world places.
- Nearby entities belong to incompatible categories and must not merge.
- Stable identifiers match even when names differ slightly.
- Sources disagree on names, categories, or coordinates for the same entity.
- Too many medium- or low-confidence candidates are generated in one run.
- QA detects suspicious merge rates, cluster sizes, or distance violations.
- Publication fails after staging passes QA.

## Use Case Flows

### Main Flow (verbatim from use case)

1. The maintainer initiates a deduplication run for relevant entity types (e.g., POIs, facilities).
2. The system collects candidate entities across sources, grouped by canonical category and geographic region.
3. The system generates duplicate candidates using matching rules:
   - spatial proximity (within a configured distance threshold)
   - normalized name similarity (case/spacing/abbreviation handling)
   - category agreement (same canonical category or compatible categories)
   - stable identifiers when available (e.g., shared IDs)
4. The entity resolution module assigns a confidence score to each candidate match.
5. The system merges high-confidence duplicates into a single canonical entity and links all source records to it.
6. The system flags low-confidence candidates for review and does not merge them automatically (or merges only with strict rules, depending on policy).
7. The system runs QA checks:
   - count reduction summary by category and source
   - spot checks for over-merging (distinct entities incorrectly merged)
   - distance threshold sanity checks
8. The system publishes the deduplicated canonical entities for downstream feature computation and records a deduplication run report.

### Alternate Flows (verbatim from use case extensions)

- **3a**: Two entities are close but distinct (e.g., adjacent businesses)
  - **3a1**: The system assigns low confidence and does not merge automatically.
  - **3a2**: The maintainer refines matching thresholds or adds disambiguation rules (e.g., unit number, address, distinct names).
- **5a**: Conflicting attributes across sources (different names, categories, coordinates)
  - **5a1**: The system applies precedence rules (preferred source, latest update, higher-quality dataset).
  - **5a2**: The system stores conflicting values for audit and chooses a canonical representation.
- **6a**: Too many low-confidence candidates are produced
  - **6a1**: The system outputs a review report and suggests tighter match rules.
  - **6a2**: The maintainer updates rules and reruns.
- **8a**: Downstream computations rely on source-specific entities (require provenance)
  - **8a1**: The system retains source links so features can use canonical entities while preserving source traceability.

### Exception / Error Flows (verbatim from use case extensions)

- No separate exception flow is defined in `Use Cases/UC-21.md`; failure handling is covered by the failed end condition and extension outcomes above.

## Requirements *(mandatory)*

### Feature Details

#### Data Involved

- Candidate entities from multiple sources with provenance fields such as source and source ID
- Canonical categories and geographic regions used to group candidate entities
- Matching evidence: spatial proximity, normalized name similarity, category agreement or compatibility, and stable identifiers when available
- Confidence scores assigned to candidate matches
- Canonical entities produced by merging duplicate source records
- Canonical-to-source link records connecting canonical entities to contributing source rows
- Review candidates and low-confidence candidate outputs
- QA outputs: count reduction by category and source, over-merge checks, distance sanity checks
- Run metadata: run ID, thresholds, scoring version or rules, counts, warnings, publication status
- Conflicting source attributes retained for audit

#### Implementation Constraints

- The feature implementation must remain within Python and vanilla HTML/CSS/JS project constraints.

### Functional Requirements

- **FR-01-001**: The system MUST allow the maintainer to initiate a deduplication run for relevant entity types.
- **FR-01-002**: The system MUST collect candidate entities across sources and group them by canonical category and geographic region.
- **FR-01-003**: The system MUST generate duplicate candidates using configured matching rules based on spatial proximity, normalized name similarity, category agreement or compatibility, and stable identifiers when available.
- **FR-01-004**: The entity resolution module MUST assign a confidence score to each candidate match.
- **FR-01-005**: The system MUST merge high-confidence duplicates into a single canonical entity and link all contributing source records to that canonical entity.
- **FR-01-006**: The system MUST place medium-confidence candidates into a review list and MUST NOT merge them silently.
- **FR-01-007**: The system MUST reject low-confidence candidates from automatic merge and MUST NOT place them into the review list by default.
- **FR-01-008**: When entities are close but distinct, the system MUST assign low confidence and MUST NOT merge them automatically.
- **FR-01-009**: The system MUST allow the maintainer to refine matching thresholds or add disambiguation rules and rerun deduplication.
- **FR-01-010**: When source attributes conflict, the system MUST choose the canonical representation by preferring the configured preferred source first, then the highest-quality source, then the most recent update, and it MUST preserve conflicting values for audit.
- **FR-01-011**: When too many low-confidence candidates are produced, the system MUST output a review report and suggest tighter match rules.
- **FR-01-012**: The system MUST retain source links so downstream features can use canonical entities while preserving source traceability.
- **FR-01-013**: The system MUST run QA checks that summarize count reduction by category and source, check for over-merging, and validate distance-threshold sanity.
- **FR-01-014**: The system MUST block publication when QA detects suspicious merges or violated deduplication constraints and MUST preserve the last known-good production canonical entities.
- **FR-01-015**: The system MUST publish deduplicated canonical entities and canonical-to-source link tables atomically for downstream feature computation.
- **FR-01-016**: The system MUST record a deduplication run report with run ID, thresholds or scoring-version identifiers, counts before and after, merges performed, review candidates, rejected candidates, warnings, and publication status.
- **FR-01-017**: The system MUST produce deterministic canonical-entity assignments for the same inputs and deduplication configuration.
- **FR-01-018**: The system MUST treat stable identifier matches as merge evidence that can increase confidence appropriately.
- **FR-01-019**: The system MUST prevent merges across incompatible categories, even when entities are spatially close.
- **FR-01-020**: If publication fails, the system MUST report actionable failure details, preserve the last known-good production canonical entities, and MUST NOT record the failed run as a successful production version.
- **FR-01-021**: After successful publication, downstream queries that count amenities by canonical category MUST operate on canonical entities rather than raw source records so the same real-world place is counted once.

### Non-Functional Requirements

- **NFR-001**: Deduplication must complete within an agreed operational window for target POI volumes and configured thresholds.
- **NFR-002**: QA and publication failures must not corrupt production data, and low-confidence matches must not be silently merged.
- **NFR-003**: Each run must be auditable by run ID and retain configuration snapshots, merge counts, review candidates, QA outcomes, and publication status.

### Key Entities *(include if feature involves data)*

- **Candidate Entity**: A source-specific open-data record considered for deduplication, including provenance, geometry, names, categories, and optional stable IDs.
- **Canonical Entity**: The deduplicated representation of one real-world place formed from one or more source-specific records.
- **Canonical-to-Source Link**: The association between a canonical entity and each contributing source record, preserving provenance and auditability.
- **Review Candidate**: A medium-confidence potential duplicate that is not merged automatically and is retained for review or rerun decisions.
- **Deduplication Run Metadata**: The audit record for one deduplication execution, including thresholds, scoring identifiers, counts, QA outputs, warnings, and publication status.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-21-01 | FR-01-005, FR-01-012, FR-01-015, FR-01-016 |
| AT-21-02 | FR-01-002, FR-01-003, FR-01-016, FR-01-018 |
| AT-21-03 | FR-01-004, FR-01-005, FR-01-006, FR-01-007 |
| AT-21-04 | FR-01-016, FR-01-017 |
| AT-21-05 | FR-01-006, FR-01-007, FR-01-008, FR-01-013 |
| AT-21-06 | FR-01-003, FR-01-019 |
| AT-21-07 | FR-01-018 |
| AT-21-08 | FR-01-010, FR-01-012 |
| AT-21-09 | FR-01-013, FR-01-014 |
| AT-21-10 | FR-01-015, FR-01-016 |
| AT-21-11 | FR-01-020 |
| AT-21-12 | FR-01-021 |

#### Flow Steps to Functional Requirements

| Flow Step / Section | Related FRs |
| --- | --- |
| Main Flow 1 | FR-01-001 |
| Main Flow 2 | FR-01-002 |
| Main Flow 3 | FR-01-003, FR-01-018, FR-01-019 |
| Main Flow 4 | FR-01-004 |
| Main Flow 5 | FR-01-005, FR-01-010, FR-01-012 |
| Main Flow 6 | FR-01-006, FR-01-007 |
| Main Flow 7 | FR-01-013, FR-01-014 |
| Main Flow 8 | FR-01-015, FR-01-016, FR-01-021 |
| Alternate Flows 3a / 5a / 6a / 8a | FR-01-008, FR-01-009, FR-01-010, FR-01-011, FR-01-012 |
| Exception / Error Handling | FR-01-014, FR-01-020 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid deduplication runs produce canonical entities and canonical-to-source links for the targeted input records.
- **SC-002**: 100% of runs with QA failures or publication failures preserve the last known-good production canonical-entity version.
- **SC-003**: 100% of repeated runs with identical inputs and deduplication configuration produce identical canonical-entity assignments.
- **SC-004**: 100% of successful published runs allow downstream canonical-category counts to avoid double-counting the same real-world place across sources.
