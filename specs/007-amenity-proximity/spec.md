# Feature Specification: Compute Proximity to Amenities for Baseline Desirability

**Feature Branch**: `007-amenity-proximity`  
**Created**: 2026-03-09  
**Status**: Draft  
**Input**: User description: "Generate a feature specification for UC-07 using `Use Cases/UC-07.md` and `Acceptance Tests/UC-07-AT.md` as the sources of truth, preserving use case flows and deriving only supported functional requirements."

## Use Case Overview

**Summary / Goal**: Enable the valuation engine to compute proximity to key amenities for a canonical location ID so baseline desirability can be derived as part of valuation.

**Actors**:
- Primary Actor: Valuation Engine
- Secondary Actors: Spatial Database; POI Dataset Service; Routing/Distance Service

**Preconditions**:
- The canonical location ID has already been generated.
- Open-data POI datasets (schools, parks, hospitals) are available and indexed.
- The spatial database is operational.
- Distance computation mechanisms (e.g., straight-line or routing-based) are available.

**Trigger**: The valuation engine receives a canonical location ID and initiates feature computation for valuation.

**Main Flow (verbatim)**:
1. The valuation engine receives a canonical location ID for a property.
2. The system retrieves the geographic coordinates associated with the canonical location ID.
3. The system queries the spatial database for relevant amenities within a predefined search radius.
4. The system computes the distance from the property location to each relevant amenity.
5. The system aggregates proximity metrics (e.g., nearest school distance, number of parks within radius, nearest hospital distance).
6. The system derives a baseline desirability score based on predefined weighting rules.
7. The system attaches the computed proximity features and desirability score to the property's feature set for valuation.

**Alternate Flows (verbatim)**:
- **3a**: No amenities found within search radius
  - 3a1: The system records zero-count or maximum-distance values according to predefined rules.
  - 3a2: The system continues to Step 6 using fallback scoring logic.
- **4a**: Distance computation service unavailable
  - 4a1: The system falls back to straight-line (Euclidean) distance if routing-based distance fails.
  - 4a2: The system logs the fallback usage.
  - 4a3: The scenario resumes at Step 5.
- **6a**: Weighting rules missing or misconfigured
  - 6a1: The system applies default weighting parameters.
  - 6a2: The system logs configuration fallback.

**Exception / Error Flows (verbatim)**:
- **2a**: Canonical location ID cannot be resolved to coordinates
  - 2a1: The system logs the failure.
  - 2a2: The system omits proximity features and proceeds without desirability adjustment.

**Data Involved (use case only)**:
- Canonical location ID
- Geographic coordinates
- Relevant amenities
- Search radius
- Distance
- Proximity metrics
- Nearest school distance
- Number of parks within radius
- Nearest hospital distance
- Baseline desirability score
- Weighting rules
- Property's feature set

## Assumptions & Constraints

- Implementation constraints: Python, vanilla HTML/CSS/JS.
- Scope is limited to computing proximity features, fallback handling, omission handling, and desirability scoring behaviors defined in UC-07 and UC-07-AT.

## Clarifications

### Session 2026-03-09

- Q: When coordinates cannot be resolved for the canonical location ID, should the system omit desirability adjustment entirely or set an explicit neutral default? → A: Omit desirability adjustment entirely.
- Q: Which distance method should be used by default for normal proximity computation? → A: Use routing-based distance by default; fall back to Euclidean only when routing fails.
- Q: Should the predefined search radius be shared across all amenity categories or defined separately per category? → A: Use one shared search radius for all amenity categories.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute Proximity Features (Priority: P1)

As the valuation engine, I want to compute amenity proximity metrics and a desirability score for a canonical location so those features can be attached to the property for valuation.

**Why this priority**: This is the core subfunction invoked for every valuation request.

**Independent Test**: Run proximity feature computation for a canonical location that resolves to coordinates and has amenity data within the configured radius, then verify numeric proximity metrics and a numeric desirability score are attached to the feature set.

**Acceptance Scenarios**:

1. **Given** a valid canonical location ID, resolved coordinates, amenity data within the configured search radius, available distance computation, and configured weighting rules, **When** the valuation engine triggers proximity feature computation, **Then** the system queries amenities, computes distances, aggregates proximity metrics, derives a desirability score, and attaches both metrics and score to the feature set. (AT-01)
2. **Given** proximity metrics are computed successfully, **When** the feature set is produced, **Then** all distance metrics are non-negative numbers, count metrics are non-negative integers, units are consistent, and nearest-distance metrics do not exceed the configured maximum-distance sentinel when one is used. (AT-06)
3. **Given** the same canonical location ID, the same POI dataset snapshot, and the same configuration, **When** proximity computation runs multiple times, **Then** the proximity metrics and desirability score are identical on each run within the allowed floating-point tolerance. (AT-07)

---

### User Story 2 - Continue with Fallback Values (Priority: P2)

As the valuation engine, I want deterministic fallback behavior when amenity results, routing distances, or weighting rules are unavailable so valuation can still use usable proximity-based features.

**Why this priority**: These fallback paths preserve required valuation input under common dependency and data gaps.

**Independent Test**: Run the computation with missing amenities, unavailable routing distance, or misconfigured weighting, then verify the defined fallback values or methods are used and the resulting desirability score is still attached.

**Acceptance Scenarios**:

1. **Given** coordinates resolve but no amenities of one or more categories exist within the configured radius, **When** proximity computation runs, **Then** the system records zero-count or maximum-distance fallback values, still computes a desirability score using fallback scoring logic, and attaches the features to the feature set. (AT-02)
2. **Given** coordinates resolve, amenities exist within radius, routing-based distance fails, and Euclidean fallback is enabled, **When** proximity computation runs, **Then** the system logs the routing failure, uses Euclidean distance, produces proximity metrics and desirability score, and records that the fallback distance method was used. (AT-03)
3. **Given** coordinates resolve and proximity metrics are available but weighting configuration is missing or invalid, **When** proximity computation runs, **Then** the system logs the weighting configuration issue, applies default weighting parameters, and attaches the resulting desirability score and features. (AT-05)

---

### User Story 3 - Omit Proximity When Coordinates Cannot Be Resolved (Priority: P3)

As the valuation engine, I want coordinate-resolution failure to be handled explicitly so downstream valuation can continue without invalid proximity features.

**Why this priority**: Coordinate resolution failure blocks all spatial querying and must stop proximity computation cleanly.

**Independent Test**: Run proximity computation with a canonical location ID that cannot be resolved to coordinates and verify the failure is logged, no proximity metrics are computed, and downstream valuation continues without proximity features.

**Acceptance Scenarios**:

1. **Given** canonical location ID lookup fails, **When** proximity feature computation runs, **Then** the system logs the failure, omits proximity metrics, omits desirability adjustment, and continues downstream valuation without proximity features. (AT-04)

### Edge Cases

- No amenities of one or more categories are found within the configured search radius.
- Routing-based distance computation fails and Euclidean fallback is used.
- Canonical location ID lookup fails and coordinates cannot be resolved.
- Weighting rules are missing or misconfigured.
- Proximity outputs must remain deterministic for the same canonical location ID, dataset snapshot, radius, weights, and distance method.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-01-001**: The system MUST accept a canonical location ID for a property as the input to proximity feature computation. (Main Flow Step 1, AT-01)
- **FR-01-015**: The system MUST retrieve the geographic coordinates associated with the canonical location ID before querying for amenities. (Main Flow Step 2, AT-01, AT-04)
- **FR-01-030**: The system MUST query the spatial database for relevant amenities within one predefined search radius shared across all amenity categories. (Main Flow Step 3, AT-01)
- **FR-01-045**: The system MUST compute the distance from the property location to each relevant amenity using routing-based distance by default. (Main Flow Step 4, AT-01)
- **FR-01-060**: The system MUST aggregate proximity metrics including, at minimum, nearest school distance, number of parks within radius, and nearest hospital distance. (Main Flow Step 5, AT-01)
- **FR-01-075**: The system MUST derive a baseline desirability score based on predefined weighting rules. (Main Flow Step 6, AT-01)
- **FR-01-090**: The system MUST attach the computed proximity features and desirability score to the property's feature set for valuation. (Main Flow Step 7, AT-01)
- **FR-01-098**: The feature set MUST contain the correct fields for all configured amenity categories. (AT-01)
- **FR-01-105**: If no amenities are found within the search radius for one or more categories, the system MUST record zero-count or maximum-distance values according to predefined rules. (Alternate Flow 3a, AT-02)
- **FR-01-120**: If no amenities are found within the search radius for one or more categories, the system MUST continue to scoring using fallback scoring logic and still attach the resulting features to the feature set. (Alternate Flow 3a, AT-02)
- **FR-01-135**: If the distance computation service is unavailable, the system MUST fall back to straight-line (Euclidean) distance when the default routing-based distance fails. (Alternate Flow 4a, AT-03)
- **FR-01-150**: If the distance computation service falls back from routing-based distance to Euclidean distance, the system MUST log the fallback usage. (Alternate Flow 4a, AT-03)
- **FR-01-165**: If the distance computation service falls back from routing-based distance to Euclidean distance, the system MUST still produce proximity metrics and a desirability score. (Alternate Flow 4a, AT-03)
- **FR-01-180**: If the canonical location ID cannot be resolved to coordinates, the system MUST log the failure. (Exception Flow 2a, AT-04)
- **FR-01-195**: If the canonical location ID cannot be resolved to coordinates, the system MUST omit proximity features and proceed without desirability adjustment. (Exception Flow 2a, AT-04)
- **FR-01-210**: If the canonical location ID cannot be resolved to coordinates, the system MUST NOT call POI or distance services after the coordinate-resolution failure. (AT-04)
- **FR-01-225**: If weighting rules are missing or misconfigured, the system MUST apply default weighting parameters. (Alternate Flow 6a, AT-05)
- **FR-01-240**: If weighting rules are missing or misconfigured, the system MUST log the configuration fallback. (Alternate Flow 6a, AT-05)
- **FR-01-255**: If weighting rules are missing or misconfigured, the system MUST still derive a desirability score and attach the features. (Alternate Flow 6a, AT-05)
- **FR-01-270**: Successful proximity outputs MUST keep distance metrics as non-negative numbers, count metrics as non-negative integers, and units consistent across the feature set. (AT-06)
- **FR-01-285**: When nearest-distance sentinel values are used, nearest-distance metrics MUST be less than or equal to the configured maximum-distance sentinel. (AT-06)
- **FR-01-300**: For the same canonical location ID, POI dataset snapshot, shared search radius, weighting configuration, and distance method, proximity metrics and desirability score MUST be deterministic across repeated runs within floating-point tolerance. (AT-07)

### Non-Functional Requirements

- **NFR-01-001**: Implementation is constrained to Python with vanilla HTML/CSS/JS interfaces where user-facing interaction is required.

### Key Entities *(include if feature involves data)*

- **Canonical Location ID**: The property location identifier used to resolve geographic coordinates for proximity computation.
- **Amenity Proximity Metrics**: The aggregated proximity values derived from nearby amenities, including nearest school distance, parks count within radius, and nearest hospital distance.
- **Baseline Desirability Score**: The score derived from proximity metrics using configured or default weighting rules.
- **Amenity Query Result Set**: The amenities found within the search radius, or fallback values when amenities are absent for one or more categories.
- **Property Feature Set**: The valuation feature collection to which proximity metrics and desirability score are attached.

### Traceability

**Acceptance Tests → Functional Requirements**:
- **AT-01** → FR-01-001, FR-01-015, FR-01-030, FR-01-045, FR-01-060, FR-01-075, FR-01-090, FR-01-098
- **AT-02** → FR-01-105, FR-01-120
- **AT-03** → FR-01-135, FR-01-150, FR-01-165
- **AT-04** → FR-01-015, FR-01-180, FR-01-195, FR-01-210
- **AT-05** → FR-01-225, FR-01-240, FR-01-255
- **AT-06** → FR-01-270, FR-01-285
- **AT-07** → FR-01-300

**Flow Steps / Sections → Functional Requirements (coarse)**:
- **Main Flow Step 1** → FR-01-001
- **Main Flow Step 2** → FR-01-015
- **Main Flow Step 3** → FR-01-030
- **Main Flow Step 4** → FR-01-045
- **Main Flow Step 5** → FR-01-060
- **Main Flow Step 6** → FR-01-075
- **Main Flow Step 7** → FR-01-090
- **Alternate Flow 3a** → FR-01-105, FR-01-120
- **Alternate Flow 4a** → FR-01-135, FR-01-150, FR-01-165
- **Exception Flow 2a** → FR-01-180, FR-01-195, FR-01-210
- **Alternate Flow 6a** → FR-01-225, FR-01-240, FR-01-255

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-01-001**: 100% of successful proximity computations with resolved coordinates, configured search radius, amenity data, and valid weighting rules return numeric proximity metrics and a numeric desirability score attached to the property feature set. (AT-01)
- **SC-01-002**: 100% of runs with no amenities found within the configured radius return deterministic fallback metric values and still produce a desirability score. (AT-02)
- **SC-01-003**: 100% of runs where routing-based distance fails and Euclidean fallback is enabled still produce proximity metrics and a desirability score while recording fallback usage. (AT-03)
- **SC-01-004**: 100% of coordinate-resolution failures log the failure, produce no proximity metrics, and continue downstream valuation without calling POI or distance services afterward. (AT-04)
- **SC-01-005**: 100% of runs with missing or invalid weighting configuration apply default weighting parameters and still produce a desirability score. (AT-05)
- **SC-01-006**: 100% of successful outputs keep distance metrics non-negative, count metrics as non-negative integers, and units consistent. (AT-06)
- **SC-01-007**: 100% of repeated runs with identical inputs and configuration produce identical integer outputs and floating-point outputs within tolerance. (AT-07)
