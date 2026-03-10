# Feature Specification: Compute Neighbourhood Indicators for Local Context

**Feature Branch**: `[012-neighbourhood-indicators]`  
**Created**: 2026-03-09  
**Status**: Draft  
**Input**: User description referencing `Use Cases/UC-12.md`, `Scenarios/UC-12-Scenarios.md`, and `Acceptance Tests/UC-12-AT.md`

## Overview

### Feature Name

Compute Neighbourhood Indicators for Local Context

### Summary / Goal

Enable the system to compute neighbourhood-level indicators for a property so that users can understand the broader local context surrounding the property.

### Actors

- **Primary Actor**: Valuation Engine
- **Secondary Actors**: Spatial Database; Census/Neighbourhood Dataset Service; Statistical Aggregation Service

### Preconditions

- A valid canonical location ID has been generated.
- The canonical location ID can be resolved to geographic coordinates or a spatial unit.
- Neighbourhood boundary datasets (e.g., census tracts, planning districts) are available and indexed.
- Relevant statistical datasets (e.g., demographics, income levels, crime rates, density metrics) are available.

### Trigger

The valuation engine requires neighbourhood context features during feature computation for a canonical location ID.

### Assumptions

- `Use Cases/UC-12.md` is the source of truth for flows, actors, preconditions, and trigger.
- `Acceptance Tests/UC-12-AT.md` is the source of truth for verifiable behavior and output checks.
- `Scenarios/UC-12-Scenarios.md` was not required to resolve missing behavior for this initial specification.

## Clarifications

### Session 2026-03-09

- Q: On coordinate-resolution failure, should the system omit neighbourhood features or return neutral defaults? → A: Omit neighbourhood indicators and composite profile, and explicitly mark them absent.
- Q: Which boundary-resolution policy should apply when a property does not map cleanly to one neighbourhood boundary? → A: Apply the configured deterministic policy, such as nearest-centroid, largest-overlap, or a deterministic tie-break rule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute Neighbourhood Context (Priority: P1)

As the valuation process, I need neighbourhood indicators and a summarized neighbourhood context profile for a property so the property feature set reflects broader local conditions.

**Why this priority**: This is the core success path and the primary feature value.

**Independent Test**: Can be fully tested by resolving a property to a single neighbourhood boundary with available statistical data and verifying that indicators and the composite profile are attached to the feature set.

**Acceptance Scenarios**:

1. **Given** a valid canonical location ID, resolved property coordinates, a neighbourhood boundary dataset containing the property within exactly one boundary, available statistical datasets, and present composite weighting configuration, **When** neighbourhood context computation runs, **Then** the system maps the property to a boundary, retrieves indicators, normalizes or aggregates them as required, derives the summarized profile, and attaches the results to the property's feature set. (`AT-01`)
2. **Given** successfully retrieved and normalized indicators but missing or invalid composite weighting configuration, **When** composite profile derivation runs, **Then** the system applies default weights or thresholds, derives the composite neighbourhood profile, and indicates that defaults were used. (`AT-05`)

---

### User Story 2 - Continue When Mapping or Data Are Imperfect (Priority: P2)

As the valuation process, I need neighbourhood context computation to handle missing coordinates, ambiguous boundary membership, and incomplete datasets without blocking valuation.

**Why this priority**: These are key fallback and continuation paths, but they build on the primary neighbourhood computation flow.

**Independent Test**: Can be tested by forcing coordinate-resolution failure, multi-boundary edge cases, or missing statistical data and verifying omission, deterministic boundary selection, or fallback-value behavior.

**Acceptance Scenarios**:

1. **Given** coordinate-resolution failure, **When** neighbourhood context computation runs, **Then** the system logs the failure, avoids boundary lookup, omits neighbourhood indicators and composite profile while explicitly marking them absent, and proceeds without context features. (`AT-02`)
2. **Given** coordinates that lie on a boundary edge or intersect multiple neighbourhood polygons and a configured resolution policy, **When** neighbourhood boundary resolution runs, **Then** the system applies the configured policy, logs the resolution method, deterministically selects a single boundary, and continues normal flow for that boundary. (`AT-03`)
3. **Given** successful boundary mapping but unavailable or incomplete statistical datasets and available fallback values, **When** indicator retrieval runs, **Then** the system logs the dataset issue, uses fallback values for missing indicators, derives the composite profile using available and fallback values, and indicates fallback usage. (`AT-04`)

---

### User Story 3 - Preserve Indicator Integrity and Repeatability (Priority: P3)

As a downstream consumer of neighbourhood context features, I need normalized indicators and the composite profile to satisfy range and determinism constraints so the outputs can be trusted.

**Why this priority**: Data-quality guarantees matter after the core and fallback flows are defined.

**Independent Test**: Can be tested by validating output invariants and repeating the same run with identical data snapshots and configuration to confirm stable results.

**Acceptance Scenarios**:

1. **Given** indicators are computed and normalized, **When** output is produced, **Then** normalized indicators remain within configured ranges, raw indicators obey domain constraints, no NaN or Infinity values appear, and units remain consistent with dataset definitions. (`AT-06`)
2. **Given** the same canonical location ID, boundary dataset snapshot, statistical dataset snapshots, normalization rules, and composite configuration, **When** neighbourhood context computation runs multiple times, **Then** boundary selection, indicators, and composite profile remain identical across runs within floating-point tolerance. (`AT-07`)

### Edge Cases

- Canonical location ID cannot be resolved to coordinates.
- The property does not map cleanly to a single neighbourhood boundary.
- Statistical datasets are unavailable or incomplete.
- Composite weighting configuration is missing or invalid.

## Requirements *(mandatory)*

### Main Flow

1. The valuation engine receives a canonical location ID for a property.
2. The system retrieves the geographic coordinates associated with the canonical location ID.
3. The system determines the corresponding neighbourhood boundary (e.g., census tract or district) that contains the property.
4. The system retrieves neighbourhood-level indicators from statistical datasets. Examples may include:
   - Population density
   - Median household income
   - Crime rate index
   - Housing density or tenure mix
5. The system aggregates and normalizes the retrieved indicators as required.
6. The system derives a summarized neighbourhood context profile or composite indicator based on predefined rules.
7. The system attaches the individual neighbourhood indicators and the summarized profile to the property's feature set.

### Alternate Flows

- **3a**: Property does not map cleanly to a neighbourhood boundary
  - **3a1**: The system applies nearest-boundary or centroid-based assignment logic.
  - **3a2**: The system logs the boundary resolution method used.
- **4a**: Statistical dataset unavailable or incomplete
  - **4a1**: The system logs dataset issue.
  - **4a2**: The system applies fallback values (e.g., regional averages or cached values).
  - **4a3**: The scenario resumes at Step 6.

### Exception/Error Flows

- **2a**: Canonical location ID cannot be resolved to coordinates
  - **2a1**: The system logs the failure.
  - **2a2**: The system omits neighbourhood computation and proceeds without context features.
- **6a**: Composite weighting configuration missing
  - **6a1**: The system applies default neighbourhood weighting parameters.
  - **6a2**: The system logs configuration fallback.

### Data Involved

- **Canonical location ID**: The property identifier used to trigger neighbourhood context computation.
- **Geographic coordinates**: The resolved property coordinates used for neighbourhood boundary mapping.
- **Neighbourhood boundary dataset**: The indexed set of census tracts, planning districts, or other neighbourhood boundaries used to map the property.
- **Corresponding neighbourhood boundary**: The resolved boundary that contains or is assigned to the property.
- **Boundary resolution policy**: The configured deterministic policy used when a property lies on an edge, overlaps multiple polygons, or otherwise does not map cleanly to a single boundary.
- **Neighbourhood-level indicators**: Retrieved statistics such as population density, median household income, crime rate index, housing density, or tenure mix.
- **Aggregated and normalized indicators**: The processed neighbourhood indicators prepared for composite profile derivation.
- **Summarized neighbourhood context profile or composite indicator**: The derived profile based on predefined rules.
- **Property feature set**: The output collection that receives neighbourhood indicators and the summarized profile.
- **Fallback values**: Regional averages or cached values used when statistical datasets are unavailable or incomplete.
- **Default neighbourhood weighting parameters**: The fallback weights used when composite weighting configuration is missing.

### Functional Requirements

- **FR-01-001**: The system MUST accept a canonical location ID for a property as input for neighbourhood context computation.
- **FR-01-002**: The system MUST retrieve the geographic coordinates associated with the canonical location ID before neighbourhood computation continues.
- **FR-01-003**: The system MUST determine the neighbourhood boundary that contains the property.
- **FR-01-004**: The system MUST retrieve configured neighbourhood-level indicators from statistical datasets for the resolved boundary.
- **FR-01-005**: The system MUST aggregate and normalize retrieved neighbourhood indicators as required.
- **FR-01-006**: The system MUST derive a summarized neighbourhood context profile or composite indicator based on predefined rules.
- **FR-01-007**: The system MUST attach the individual neighbourhood indicators and the summarized profile to the property's feature set.
- **FR-01-008**: If the canonical location ID cannot be resolved to coordinates, the system MUST log the failure, avoid boundary lookup, omit neighbourhood indicators and the composite profile, and proceed without context features.
- **FR-01-009**: If the property does not map cleanly to a neighbourhood boundary, the system MUST apply the configured deterministic boundary-resolution policy, such as nearest-centroid, largest-overlap, or a deterministic tie-break rule, log the boundary resolution method used, and select a single boundary deterministically.
- **FR-01-010**: If statistical datasets are unavailable or incomplete, the system MUST log the dataset issue, apply fallback values such as regional averages or cached values for missing indicators, resume composite-profile derivation, and indicate fallback usage.
- **FR-01-011**: If composite weighting configuration is missing or invalid, the system MUST apply default neighbourhood weighting parameters, log the configuration fallback, and still derive and attach the summarized neighbourhood profile.
- **FR-01-012**: The system MUST include boundary ID, boundary name, or equivalent boundary metadata in output metadata.
- **FR-01-013**: The system MUST ensure all configured neighbourhood indicators are present and non-empty when computation succeeds, except where fallback policy explicitly applies.
- **FR-01-014**: The system MUST ensure the summarized neighbourhood context profile is present and non-empty when computation succeeds.
- **FR-01-015**: The system MUST ensure normalized indicators fall within configured ranges.
- **FR-01-016**: The system MUST ensure raw neighbourhood indicators obey domain constraints, including non-negative density and non-negative income.
- **FR-01-017**: The system MUST ensure no NaN or Infinity values appear in neighbourhood indicators or the summarized profile.
- **FR-01-018**: The system MUST keep units consistent with dataset definitions for neighbourhood indicators.
- **FR-01-019**: The system MUST make omission, fallback-value usage, boundary-resolution method usage, or default-weight usage explicit in output or processing metadata when those conditions occur, including explicit indication that neighbourhood features are absent after coordinate-resolution failure.
- **FR-01-020**: For identical canonical location ID, boundary dataset snapshot, statistical dataset snapshots, normalization rules, and composite configuration, the system MUST produce identical boundary selection, neighbourhood indicators, and summarized profile outputs across runs within categorical exact-match and numeric tolerance expectations.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-01 | FR-01-001, FR-01-002, FR-01-003, FR-01-004, FR-01-005, FR-01-006, FR-01-007, FR-01-012, FR-01-013, FR-01-014 |
| AT-02 | FR-01-008, FR-01-019 |
| AT-03 | FR-01-009, FR-01-019 |
| AT-04 | FR-01-010, FR-01-014, FR-01-019 |
| AT-05 | FR-01-011, FR-01-014, FR-01-019 |
| AT-06 | FR-01-015, FR-01-016, FR-01-017, FR-01-018 |
| AT-07 | FR-01-020 |

#### Flow Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow Step 1 | FR-01-001 |
| Main Flow Step 2 | FR-01-002 |
| Main Flow Step 3 | FR-01-003, FR-01-012 |
| Main Flow Step 4 | FR-01-004, FR-01-013, FR-01-018 |
| Main Flow Step 5 | FR-01-005, FR-01-015, FR-01-016, FR-01-017 |
| Main Flow Step 6 | FR-01-006, FR-01-014 |
| Main Flow Step 7 | FR-01-007 |
| Alternate Flow 3a | FR-01-009, FR-01-019 |
| Alternate Flow 4a | FR-01-010, FR-01-019 |
| Exception Flow 2a | FR-01-008, FR-01-019 |
| Exception Flow 6a | FR-01-011, FR-01-019 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of successful runs, the property feature set includes configured neighbourhood indicators and a summarized neighbourhood context profile.
- **SC-002**: In 100% of coordinate-resolution failures, no neighbourhood boundary lookup occurs and valuation proceeds without neighbourhood context features.
- **SC-003**: In 100% of successful outputs, configured indicators are present, the summarized profile is present, normalized indicators remain within configured ranges, and no NaN or Infinity values appear.
- **SC-004**: In 100% of boundary-resolution, fallback-value, or default-weight cases, the output explicitly indicates the resolution or fallback handling that was applied.
- **SC-005**: For repeated runs with identical canonical location ID, boundary dataset snapshot, statistical dataset snapshots, normalization rules, and composite configuration, categorical outputs match exactly and numeric outputs remain within defined tolerance in 100% of test runs.
