# Feature Specification: Compute Distance-to-School Signals for Family Suitability

**Feature Branch**: `[010-school-distance-signals]`  
**Created**: 2026-03-09  
**Status**: Draft  
**Input**: User description referencing `Use Cases/UC-10.md`, `Scenarios/UC-10-Scenarios.md`, and `Acceptance Tests/UC-10-AT.md`

## Overview

### Feature Name

Compute Distance-to-School Signals for Family Suitability

### Summary / Goal

Enable the system to compute distance-to-school signals for a property so that users can evaluate family suitability as part of the property assessment.

### Actors

- **Primary Actor**: Valuation Engine
- **Secondary Actors**: Spatial Database; School Dataset Service; Routing/Distance Service

### Preconditions

- A valid canonical location ID has been generated.
- The canonical location ID can be resolved to geographic coordinates.
- School dataset (e.g., elementary, middle, high schools) is available and indexed.
- Distance computation mechanisms (routing-based or Euclidean) are operational.

### Trigger

The valuation engine requires school proximity features during feature computation for a canonical location ID.

### Assumptions

- `Use Cases/UC-10.md` is the source of truth for flows, actors, preconditions, and trigger.
- `Acceptance Tests/UC-10-AT.md` is the source of truth for verifiable behavior and output checks.
- `Scenarios/UC-10-Scenarios.md` was not required to resolve any missing behavior in the specification.

## Clarifications

### Session 2026-03-09

- Q: On coordinate-resolution failure, should the system omit school features or return neutral defaults? → A: Omit school distance metrics and suitability output, and explicitly mark them absent.
- Q: Which school categories should be included for distance metrics? → A: Include all schools in the dataset and map them into elementary and secondary metric groups.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute School Distance Signals (Priority: P1)

As the valuation process, I need school distance metrics and a derived family suitability signal for a property so the property assessment can include school proximity context.

**Why this priority**: This is the primary feature outcome and the main success path in the use case.

**Independent Test**: Can be fully tested by running school proximity computation for a resolvable canonical location ID with schools inside the configured radius and verifying the attached metrics and suitability signal.

**Acceptance Scenarios**:

1. **Given** a valid canonical location ID, resolved property coordinates, available schools within the configured radius, an available distance method, and configured thresholds or weights, **When** school distance computation runs, **Then** the system computes school distances, derives the required metrics, derives the family suitability signal, and attaches the results to the feature set. (`AT-01`)
2. **Given** resolved coordinates, available school data, and no schools within the configured search radius, **When** school proximity computation runs, **Then** the system records sentinel or maximum-distance values per policy, derives the low family suitability outcome, and attaches the results to the feature set. (`AT-03`)
3. **Given** successfully computed school distance metrics but missing or invalid threshold or weighting configuration, **When** family suitability derivation runs, **Then** the system applies default parameters, derives the suitability signal, and indicates that default configuration was used. (`AT-05`)

---

### User Story 2 - Continue When Inputs or Services Fail (Priority: P2)

As the valuation process, I need school proximity computation to continue safely when coordinates cannot be resolved or routing fails so valuation does not stop.

**Why this priority**: These fallback and omission paths are essential, but only after the primary computation path exists.

**Independent Test**: Can be tested by forcing coordinate-resolution failure or routing-service failure and verifying omission or Euclidean fallback behavior.

**Acceptance Scenarios**:

1. **Given** canonical location lookup failure, **When** school proximity computation runs, **Then** the system logs the failure, avoids school dataset and routing calls, omits school distance metrics and family suitability output while explicitly marking them absent, and proceeds without family suitability adjustment. (`AT-02`)
2. **Given** routing-based distance is configured as primary, schools exist within the search radius, and the routing service fails while Euclidean fallback is enabled, **When** school proximity computation runs, **Then** the system logs the routing failure, computes Euclidean distances, derives metrics and suitability using fallback distances, and records fallback method usage. (`AT-04`)

---

### User Story 3 - Produce Valid and Repeatable Metrics (Priority: P3)

As a downstream consumer of valuation features, I need school distance metrics and family suitability outputs to satisfy invariants and remain deterministic for identical inputs so the results can be trusted.

**Why this priority**: Output quality and determinism are important validation layers after the main and fallback behaviors are defined.

**Independent Test**: Can be tested by validating output invariants and repeating the same run with identical inputs to confirm stable results.

**Acceptance Scenarios**:

1. **Given** school metrics are computed, **When** the feature set is produced, **Then** all distance values are non-negative, average distance is not less than nearest distance when based on the same set, units stay consistent across metrics, and sentinel values appear only when applicable. (`AT-06`)
2. **Given** the same canonical location ID, school dataset snapshot, and configuration, **When** computation runs multiple times, **Then** distance metrics and family suitability remain identical across runs within floating-point tolerance. (`AT-07`)

### Edge Cases

- Canonical location ID cannot be resolved to coordinates.
- No schools are found within the search radius.
- Routing or distance service becomes unavailable.
- Weighting or threshold configuration is missing or invalid.

## Requirements *(mandatory)*

### Main Flow

1. The valuation engine receives a canonical location ID for a property.
2. The system retrieves the geographic coordinates associated with the canonical location ID.
3. The system queries the school dataset to identify schools within a predefined search radius.
4. The system computes the distance (travel-based or straight-line, per configuration) from the property to each identified school.
5. The system derives distance metrics, such as:
   - Distance to nearest elementary school
   - Distance to nearest secondary school
   - Average distance to top N schools within radius
6. The system applies predefined thresholds or weighting rules to derive a family suitability signal.
7. The system attaches the school distance metrics and derived family suitability signal to the property's feature set.

### Alternate Flows

- **3a**: No schools found within search radius
  - **3a1**: The system records maximum-distance or sentinel values according to predefined rules.
  - **3a2**: The system derives a low family suitability signal based on thresholds.
- **4a**: Routing/distance service unavailable
  - **4a1**: The system logs the routing failure.
  - **4a2**: The system falls back to straight-line (Euclidean) distance.
  - **4a3**: The scenario resumes at Step 5.

### Exception/Error Flows

- **2a**: Canonical location ID cannot be resolved to coordinates
  - **2a1**: The system logs the failure.
  - **2a2**: The system omits school distance computation and proceeds without family suitability adjustment.
- **6a**: Weighting/threshold configuration missing
  - **6a1**: The system applies default family suitability thresholds or weights.
  - **6a2**: The system logs configuration fallback.

### Data Involved

- **Canonical location ID**: The property identifier used to trigger school proximity computation.
- **Geographic coordinates**: The resolved property coordinates used for school-distance computation.
- **School dataset**: The indexed set of elementary, middle, high, or secondary schools used for search and distance calculation.
- **Configured school category groups**: All schools in the dataset mapped into the metric groups used by the feature, including elementary and secondary groupings.
- **Predefined search radius**: The configured radius used to identify relevant schools.
- **Distance computation method**: The configured travel-based or straight-line method used to compute school distances.
- **Distance metrics**: Metrics derived from computed school distances, including nearest elementary, nearest secondary school, and average distance to top N schools within radius.
- **Family suitability signal**: The derived output based on distance metrics and predefined thresholds or weighting rules.
- **Property feature set**: The output collection that receives school distance metrics and the family suitability signal.
- **Threshold or weighting configuration**: The configuration used to derive the family suitability signal.
- **Maximum-distance or sentinel values**: The predefined values recorded when no schools are found within the search radius.

### Functional Requirements

- **FR-01-001**: The system MUST accept a canonical location ID for a property as input for school proximity computation.
- **FR-01-002**: The system MUST retrieve the geographic coordinates associated with the canonical location ID before school proximity computation continues.
- **FR-01-003**: The system MUST query all schools in the dataset within a predefined search radius and map them into the configured metric groups.
- **FR-01-004**: The system MUST compute the configured distance from the property to each identified school using either travel-based or straight-line distance per configuration.
- **FR-01-005**: The system MUST derive school distance metrics including distance to nearest elementary school, distance to nearest secondary school, and average distance to top N schools within the search radius.
- **FR-01-006**: The system MUST apply predefined thresholds or weighting rules to derive a family suitability signal from school distance metrics.
- **FR-01-007**: The system MUST attach school distance metrics and the derived family suitability signal to the property's feature set after successful computation.
- **FR-01-008**: If the canonical location ID cannot be resolved to coordinates, the system MUST log the failure, skip school dataset and routing calls, omit school distance metrics and family suitability output, and proceed without family suitability adjustment.
- **FR-01-009**: If no schools are found within the search radius, the system MUST record maximum-distance or sentinel values according to predefined rules, record counts as zero when applicable, and derive a low family suitability signal based on thresholds.
- **FR-01-010**: If the routing or distance service is unavailable while routing-based distance is configured and Euclidean fallback is enabled, the system MUST log the routing failure, fall back to straight-line distance, resume metric derivation, and record that fallback distance method was used.
- **FR-01-011**: If weighting or threshold configuration is missing or invalid, the system MUST apply default family suitability thresholds or weights, log the configuration fallback, and still derive and attach the family suitability signal.
- **FR-01-012**: The system MUST ensure all computed distance values are numeric and non-negative.
- **FR-01-013**: When average distance and nearest distance are computed on the same set of schools, the system MUST ensure average distance is greater than or equal to nearest distance.
- **FR-01-014**: The system MUST keep units consistent across school-distance metrics according to the configured distance unit.
- **FR-01-015**: The system MUST ensure sentinel values appear only when applicable, including when no schools are found within the search radius or a school is unreachable under the configured policy.
- **FR-01-016**: The system MUST provide metric fields for all configured school categories.
- **FR-01-016**: The system MUST provide metric fields for all configured school categories, including elementary and secondary groupings derived from the dataset.
- **FR-01-017**: The system MUST make omission, fallback-method usage, or default-configuration usage explicit in output or processing metadata when those conditions occur, including explicit indication that school-related features are absent after coordinate-resolution failure.
- **FR-01-018**: For identical canonical location ID, school dataset snapshot, and configuration, the system MUST produce identical distance metrics and family suitability outputs across runs within categorical exact-match and numeric tolerance expectations.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-01 | FR-01-001, FR-01-002, FR-01-003, FR-01-004, FR-01-005, FR-01-006, FR-01-007, FR-01-012, FR-01-016 |
| AT-02 | FR-01-008, FR-01-017 |
| AT-03 | FR-01-007, FR-01-009, FR-01-015 |
| AT-04 | FR-01-010, FR-01-017 |
| AT-05 | FR-01-011, FR-01-017 |
| AT-06 | FR-01-012, FR-01-013, FR-01-014, FR-01-015 |
| AT-07 | FR-01-018 |

#### Flow Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow Step 1 | FR-01-001 |
| Main Flow Step 2 | FR-01-002 |
| Main Flow Step 3 | FR-01-003 |
| Main Flow Step 4 | FR-01-004 |
| Main Flow Step 5 | FR-01-005, FR-01-012, FR-01-013, FR-01-014, FR-01-016 |
| Main Flow Step 6 | FR-01-006 |
| Main Flow Step 7 | FR-01-007 |
| Alternate Flow 3a | FR-01-009, FR-01-015 |
| Alternate Flow 4a | FR-01-010, FR-01-017 |
| Exception Flow 2a | FR-01-008, FR-01-017 |
| Exception Flow 6a | FR-01-011, FR-01-017 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of successful runs, the feature set includes school distance metrics for configured school categories and a family suitability signal.
- **SC-002**: In 100% of coordinate-resolution failures, no school dataset or routing calls occur and valuation proceeds without family suitability adjustment.
- **SC-003**: In 100% of successful outputs, all distance metrics are numeric and non-negative, average distance is not lower than nearest distance when computed on the same school set, and units remain consistent across metrics.
- **SC-004**: In 100% of routing failures with Euclidean fallback enabled or configuration-fallback cases, the output explicitly indicates fallback handling.
- **SC-005**: For repeated runs with identical canonical location ID, school dataset snapshot, and configuration, categorical outputs match exactly and numeric outputs remain within defined tolerance in 100% of test runs.
