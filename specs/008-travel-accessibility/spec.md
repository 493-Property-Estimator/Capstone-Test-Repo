# Feature Specification: Compute Travel-Based Distance for Accessibility

**Feature Branch**: `008-travel-accessibility`  
**Created**: 2026-03-09  
**Status**: Draft  
**Input**: User description: "Generate a feature specification for UC-08 using `Use Cases/UC-08.md` and `Acceptance Tests/UC-08-AT.md` as the sources of truth, preserving use case flows and deriving only supported functional requirements."

## Use Case Overview

**Summary / Goal**: Enable the valuation engine to compute travel-time-based accessibility between a property and relevant destinations so accessibility reflects real-world travel paths.

**Actors**:
- Primary Actor: Valuation Engine
- Secondary Actors: Routing/Distance Service; Spatial Database; Road Network Dataset

**Preconditions**:
- A valid canonical location ID has been generated.
- The canonical location ID can be resolved to geographic coordinates.
- The routing/distance service is configured.
- Road network data is available and indexed.

**Trigger**: The valuation engine requires distance calculations between a canonical location ID and one or more destinations as part of feature computation.

**Main Flow (verbatim)**:
1. The valuation engine receives a canonical location ID and a set of destination points (e.g., schools, hospitals, employment centers).
2. The system retrieves geographic coordinates for the canonical location ID.
3. The system retrieves geographic coordinates for each destination.
4. The system invokes the routing service to compute travel distance (or travel time) along the road network between the property and each destination.
5. The routing service returns travel-based distance values.
6. The system aggregates travel distance metrics (e.g., nearest destination travel time, average travel distance to category).
7. The system attaches travel-based accessibility features to the property's feature set for downstream valuation.

**Alternate Flows (verbatim)**:
- **4a**: Routing service unavailable or times out
  - 4a1: The system logs the routing failure.
  - 4a2: The system falls back to straight-line (Euclidean) distance.
  - 4a3: The scenario resumes at Step 6 using fallback distances.
- **4b**: No viable travel path found (e.g., isolated area)
  - 4b1: The system records a maximum travel distance threshold or sentinel value.
  - 4b2: The system continues with aggregation logic.
- **6a**: Destination list empty
  - 6a1: The system records zero-count or null accessibility metrics according to predefined rules.
  - 6a2: The system logs configuration issue.

**Exception / Error Flows (verbatim)**:
- **2a**: Canonical location ID cannot be resolved to coordinates
  - 2a1: The system logs the failure.
  - 2a2: The system omits travel-based features and proceeds without accessibility adjustment.

**Data Involved (use case only)**:
- Canonical location ID
- Destination points
- Geographic coordinates
- Travel distance
- Travel time
- Road network
- Travel-based distance values
- Travel distance metrics
- Nearest destination travel time
- Average travel distance to category
- Travel-based accessibility features
- Property's feature set
- Maximum travel distance threshold
- Sentinel value
- Zero-count accessibility metrics
- Null accessibility metrics

## Assumptions & Constraints

- Implementation constraints: Python, vanilla HTML/CSS/JS.
- Scope is limited to travel-based accessibility computation, Euclidean fallback behavior, unreachable-route handling, empty-destination handling, and omission behavior defined in UC-08 and UC-08-AT.

## Clarifications

### Session 2026-03-09

- Q: When the canonical location ID cannot be resolved to coordinates, should the system omit travel-based accessibility features entirely or set explicit neutral defaults? → A: Omit travel-based accessibility features entirely.
- Q: Should travel time or travel distance be the primary routing metric for accessibility? → A: Use travel time as the primary metric; distance may be secondary or supporting only.
- Q: Which transport mode should be the default for routing-based accessibility computation? → A: Use car travel as the default transport mode for routing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute Travel-Based Accessibility Features (Priority: P1)

As the valuation engine, I want to compute travel-time-based accessibility metrics for a property and destination set so downstream valuation uses real-world travel paths instead of straight-line proximity alone.

**Why this priority**: This is the core subfunction and the main success path for UC-08.

**Independent Test**: Run travel-based distance computation with a resolvable canonical location ID, valid destination coordinates, an available routing service, and road network data, then verify numeric travel-time metrics and aggregated accessibility features are attached to the property feature set.

**Acceptance Scenarios**:

1. **Given** a valid canonical location ID, valid property coordinates, a non-empty destination set with valid coordinates, an available routing service, and indexed road network data, **When** the valuation engine requests travel-based distances, **Then** the system invokes the routing service, receives travel times as the primary routing metric, aggregates travel-based metrics, and attaches travel-based accessibility features to the property feature set. (AT-01)
2. **Given** travel-based metrics are computed through routing or fallback, **When** the feature set is produced, **Then** all distances and times are non-negative, aggregated metrics obey expected relationships, sentinel values appear only for unreachable routes, and units remain consistent across outputs. (AT-06)
3. **Given** the same canonical location ID, destination list, routing configuration, and road network snapshot, **When** travel-based distance computation runs multiple times, **Then** the raw and aggregated accessibility results are identical across runs within floating-point tolerance. (AT-07)

---

### User Story 2 - Continue with Fallback Accessibility Values (Priority: P2)

As the valuation engine, I want the system to keep producing accessibility features when routing fails, routes are unreachable, or the destination list is empty so downstream valuation can still proceed deterministically.

**Why this priority**: These fallback and degraded-data paths preserve feature generation when dependencies or input completeness break down.

**Independent Test**: Run the computation with routing failure, unreachable routes, or an empty destination list, then verify the documented fallback or default metrics are attached and logged appropriately.

**Acceptance Scenarios**:

1. **Given** a valid property location and valid destinations but a routing service timeout or outage, **When** travel-based computation runs, **Then** the system logs the routing failure, computes Euclidean distances, aggregates fallback metrics into accessibility features, and attaches those fallback-based features. (AT-03)
2. **Given** valid property and destination coordinates but one or more destinations are unreachable by routing, **When** travel-based computation runs, **Then** the system records configured threshold or sentinel values for unreachable routes, continues aggregation using those values, and attaches accessibility features that reflect limited connectivity. (AT-04)
3. **Given** a resolvable canonical location ID and an empty destination list, **When** travel-based accessibility computation runs, **Then** the system does not call the routing service, records default or neutral accessibility metrics according to defined rules, and logs the configuration or upstream issue when applicable. (AT-05)

---

### User Story 3 - Omit Travel-Based Features When Property Coordinates Are Missing (Priority: P3)

As the valuation engine, I want coordinate-resolution failure for the property to stop travel-based distance computation cleanly so downstream valuation can continue without invalid accessibility features.

**Why this priority**: Without property coordinates, no travel-based route computation can occur.

**Independent Test**: Run travel-based distance computation with a canonical location ID that cannot be resolved to coordinates and verify the failure is logged, no routing call is made, and downstream valuation proceeds without travel-based accessibility features.

**Acceptance Scenarios**:

1. **Given** canonical location ID lookup fails, **When** travel-based distance computation is requested, **Then** the system logs the failure, does not call the routing service, omits travel-based accessibility features, and allows downstream valuation to continue without travel-based adjustments. (AT-02)

### Edge Cases

- The canonical location ID cannot be resolved to geographic coordinates.
- The routing service is unavailable or times out.
- One or more destinations have no viable travel path.
- The destination list is empty.
- Output metrics must remain deterministic for identical inputs and configuration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-01-001**: The system MUST accept a canonical location ID and a set of destination points as input to travel-based accessibility computation. (Main Flow Step 1, AT-01)
- **FR-01-015**: The system MUST retrieve geographic coordinates for the canonical location ID before requesting route computation. (Main Flow Step 2, AT-01, AT-02)
- **FR-01-030**: The system MUST retrieve geographic coordinates for each destination in the destination set. (Main Flow Step 3, AT-01)
- **FR-01-045**: The system MUST invoke the routing service to compute travel time as the primary metric along the road network between the property and each destination using car travel as the default transport mode. (Main Flow Step 4, AT-01)
- **FR-01-060**: The routing service output MUST provide travel-time values for the requested property-to-destination routes as the primary routing metric. (Main Flow Step 5, AT-01)
- **FR-01-075**: The system MUST aggregate travel-time metrics, including examples such as nearest destination travel time and average travel time to category. (Main Flow Step 6, AT-01)
- **FR-01-090**: The system MUST attach travel-based accessibility features to the property's feature set for downstream valuation. (Main Flow Step 7, AT-01)
- **FR-01-105**: Successful travel-based outputs MUST include present and numeric travel metrics and aggregated accessibility metrics with consistent units. (AT-01)
- **FR-01-120**: If the canonical location ID cannot be resolved to coordinates, the system MUST log the failure. (Exception Flow 2a, AT-02)
- **FR-01-135**: If the canonical location ID cannot be resolved to coordinates, the system MUST NOT call the routing service after the coordinate-resolution failure. (AT-02)
- **FR-01-150**: If the canonical location ID cannot be resolved to coordinates, the system MUST omit travel-based features and proceed without accessibility adjustment. (Exception Flow 2a, AT-02)
- **FR-01-165**: If the routing service is unavailable or times out, the system MUST log the routing failure. (Alternate Flow 4a, AT-03)
- **FR-01-180**: If the routing service is unavailable or times out and Euclidean fallback is enabled, the system MUST compute Euclidean distances between the property and destinations. (Alternate Flow 4a, AT-03)
- **FR-01-195**: If the routing service is unavailable or times out and Euclidean fallback is used, the system MUST aggregate fallback metrics into accessibility features and attach fallback-based accessibility features. (Alternate Flow 4a, AT-03)
- **FR-01-210**: If the routing service cannot find a viable travel path for one or more destinations, the system MUST record the configured maximum travel distance threshold or sentinel value for unreachable routes. (Alternate Flow 4b, AT-04)
- **FR-01-225**: If the routing service cannot find a viable travel path for one or more destinations, the system MUST continue aggregation using the configured threshold or sentinel values. (Alternate Flow 4b, AT-04)
- **FR-01-240**: If the destination list is empty, the system MUST NOT call the routing service. (Alternate Flow 6a, AT-05)
- **FR-01-255**: If the destination list is empty, the system MUST record zero-count, null, or predefined default accessibility metrics according to predefined rules. (Alternate Flow 6a, AT-05)
- **FR-01-270**: If the destination list is empty, the system MUST log the configuration issue. (Alternate Flow 6a, AT-05)
- **FR-01-285**: All computed distances and times MUST be non-negative, and aggregated metrics MUST obey expected relationships such as nearest less than or equal to average when applicable. (AT-06)
- **FR-01-300**: Sentinel values MUST appear only when a route is unreachable. (AT-06)
- **FR-01-315**: For the same canonical location ID, destination list, routing configuration, including transport mode, and road network snapshot, travel-based and aggregated accessibility results MUST be deterministic across repeated runs within floating-point tolerance. (AT-07)

### Non-Functional Requirements

- **NFR-01-001**: Implementation is constrained to Python with vanilla HTML/CSS/JS interfaces where user-facing interaction is required.

### Key Entities *(include if feature involves data)*

- **Canonical Location ID**: The property identifier used to resolve property coordinates for travel-based route computation.
- **Destination Set**: The collection of destination points, such as schools, hospitals, or employment centers, used to compute travel-based accessibility.
- **Travel-Based Metrics**: The returned route distances or travel times and their aggregated accessibility values.
- **Accessibility Features**: The aggregated travel-based features attached to the property's feature set for downstream valuation.
- **Unreachable Route Threshold**: The configured maximum travel distance threshold or sentinel value used when no viable travel path exists.

### Traceability

**Acceptance Tests → Functional Requirements**:
- **AT-01** → FR-01-001, FR-01-015, FR-01-030, FR-01-045, FR-01-060, FR-01-075, FR-01-090, FR-01-105
- **AT-02** → FR-01-015, FR-01-120, FR-01-135, FR-01-150
- **AT-03** → FR-01-165, FR-01-180, FR-01-195
- **AT-04** → FR-01-210, FR-01-225
- **AT-05** → FR-01-240, FR-01-255, FR-01-270
- **AT-06** → FR-01-285, FR-01-300
- **AT-07** → FR-01-315

**Flow Steps / Sections → Functional Requirements (coarse)**:
- **Main Flow Step 1** → FR-01-001
- **Main Flow Step 2** → FR-01-015
- **Main Flow Step 3** → FR-01-030
- **Main Flow Step 4** → FR-01-045
- **Main Flow Step 5** → FR-01-060
- **Main Flow Step 6** → FR-01-075
- **Main Flow Step 7** → FR-01-090
- **Exception Flow 2a** → FR-01-120, FR-01-135, FR-01-150
- **Alternate Flow 4a** → FR-01-165, FR-01-180, FR-01-195
- **Alternate Flow 4b** → FR-01-210, FR-01-225
- **Alternate Flow 6a** → FR-01-240, FR-01-255, FR-01-270

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-01-001**: 100% of successful travel-based accessibility computations with valid property coordinates, valid destination coordinates, an available routing service, and road network data return numeric travel metrics and numeric aggregated accessibility metrics with consistent units. (AT-01)
- **SC-01-002**: 100% of property-coordinate resolution failures log the failure, make no routing calls, and continue downstream valuation without travel-based adjustments. (AT-02)
- **SC-01-003**: 100% of routing-service failures with Euclidean fallback enabled still produce fallback-based accessibility features and record routing failure. (AT-03)
- **SC-01-004**: 100% of unreachable-route cases record the configured threshold or sentinel values exactly and continue aggregation without failing the whole computation. (AT-04)
- **SC-01-005**: 100% of empty-destination computations make no routing calls and produce deterministic default or neutral accessibility metrics. (AT-05)
- **SC-01-006**: 100% of produced metrics keep distances and times non-negative, preserve expected aggregation relationships when applicable, and use sentinel values only for unreachable routes. (AT-06)
- **SC-01-007**: 100% of repeated runs with identical inputs and configuration produce identical integer outputs and floating-point outputs within tolerance. (AT-07)
