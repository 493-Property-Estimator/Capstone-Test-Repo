# Feature Specification: Fall Back to Straight-Line Distance When Routing Fails

**Feature Branch**: `027-straight-line-fallback`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-27.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-27-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-27-AT.md Hard rules: 1) Copy the use case flows directly into spec.md (main + alternate + exception flows). Preserve ordering and intent. Do not invent steps. 2) You may make style/grammar improvements only if meaning is unchanged. 3) Extract functional requirements (FRs) ONLY from: - the flows in UC-27.md, and - the checks/expectations in UC-27-AT.md Do not add nice-to-have requirements that are not supported by those sources. 4) Keep implementation constraints: Python, vanilla HTML/CSS/JS. 5) Treat this use case as its own feature branch (branch naming suggestion is fine, but do not actually run git commands unless asked). Spec contents required: - Feature name (from use case title) - Summary / goal - Actors - Preconditions - Triggers - Main flow (verbatim from use case) - Alternate flows (verbatim) - Exception/error flows (verbatim) - Data involved (only what the use case mentions) - Functional requirements list (numbered FR-01-001, FR-01-015, ...) - Traceability section mapping: - each acceptance test to related FRs - each flow step (or flow section) to related FRs (coarse mapping is fine) Output: - Update/produce the spec.md for this feature. If Spec-Kit expects a per-feature folder/file, follow the tool’s convention, but the content must match the above constraints."

## Summary

The valuation engine must still compute an estimate when road-routing distance services are unavailable. When routing fails, the system uses straight-line distance as a fallback for distance-based features so the estimate pipeline can continue with a warning flag.

## Clarifications

### Session 2026-03-10

- Q: When straight-line fallback produces an unreasonable value, should the system adjust it first or exclude it immediately? → A: Apply capping or adjustment first; if the result is still unreasonable, exclude the factor and mark it unreliable.
- Q: Which HTTP status should be the canonical response when fallback is disabled and routing fails? → A: Always return HTTP 503.
- Q: Which HTTP status should be the canonical response for invalid or missing property coordinates? → A: Always return HTTP 422.

## Actors

- Primary actor: Valuation Engine / Estimate API
- Secondary actors: Routing Service Provider, Feature Database, Logging/Monitoring Service

## Preconditions

- Property coordinates are known.
- Target amenity coordinates (schools, parks, etc.) are known or queryable.
- System configuration allows fallback behavior.

## Triggers

- System attempts to compute road distance but receives an error or timeout from routing service.

## Implementation Constraints

- The feature must fit the existing project constraints of Python and vanilla HTML/CSS/JS.

## User Scenarios & Testing

### User Story 1 - Continue estimates during routing outages (Priority: P1)

As the estimate pipeline, I need straight-line distance fallback when routing fails so valuation can continue instead of stopping on routing outages.

**Why this priority**: This is the core outcome of UC-27 and the main protection against routing-service failures blocking estimates.

**Independent Test**: Can be fully tested by simulating healthy routing and routing timeouts, then verifying road distance is preferred when available and straight-line fallback is used with a warning when routing fails.

**Acceptance Scenarios**:

1. **Given** the routing provider is healthy, **When** an estimate requiring distance outputs is requested, **Then** road distances are used and no fallback flag is returned.
2. **Given** the routing provider times out and fallback is enabled, **When** an estimate is requested, **Then** the estimate completes successfully, straight-line distance is returned, fallback metadata is present, a warning is included, confidence is reduced, and logs capture the routing timeout and fallback use.

---

### User Story 2 - Handle partial routing failures without stopping the estimate (Priority: P2)

As the estimate pipeline, I need mixed-mode handling when some routing targets fail and others succeed so the estimate can complete using the best available distance data.

**Why this priority**: The use case explicitly includes mixed road-distance and fallback-distance behavior as an alternate flow.

**Independent Test**: Can be tested by requesting estimates with multiple targets, forcing partial routing failures, and verifying road distances are kept where available while straight-line fallback is used for failed targets.

**Acceptance Scenarios**:

1. **Given** multiple routing targets and only some fail, **When** an estimate is requested, **Then** the result uses road distance for successful targets, straight-line fallback for failed targets, and mixed-mode indicators in the response.

---

### User Story 3 - Return controlled errors when fallback cannot be used (Priority: P3)

As the estimate pipeline, I need controlled failure responses when fallback is disabled or coordinates are invalid so callers receive explicit failure outcomes instead of silent degradation.

**Why this priority**: The use case and acceptance tests both require defined failure behavior for disabled fallback and invalid coordinates.

**Independent Test**: Can be tested by disabling fallback or sending invalid coordinates during routing failure and verifying controlled error responses, no computed distances, and traceable request identifiers when applicable.

**Acceptance Scenarios**:

1. **Given** fallback is disabled and routing fails, **When** an estimate requiring routing distances is requested, **Then** a controlled dependency error is returned with a correlation ID.
2. **Given** invalid coordinates and routing failure, **When** an estimate request is sent, **Then** validation fails and no distances are computed.

### Edge Cases

- Routing provider returns partial results for some targets and failures for others.
- Property coordinates are missing or invalid.
- Target amenity coordinates are unavailable.
- Straight-line fallback is disabled by configuration.
- Straight-line approximation produces an unreasonable value.

## Main Flow

## Main Success Scenario

1. **Estimate API** requests distance computations for a property (road distance preferred).
2. **Distance Service** queries the routing provider for road distance.
3. **Routing provider** fails to respond within time limit or returns an error.
4. **Distance Service** detects the failure and marks road distance as unavailable.
5. **Distance Service** computes straight-line distance using property and target coordinates.
6. **Distance Service** returns straight-line distance value to the Valuation Engine with a fallback flag.
7. **Valuation Engine** uses straight-line distance for distance-based adjustments.
8. **Estimate API** includes a warning indicator in the response stating routing fallback was used.
9. **Logging/Monitoring Service** records routing outage metrics and fallback usage count.

## Alternate Flows

## Extensions

- **3a**: Routing provider returns partial result (some targets computed, others fail)
  - **3a1**: Distance Service returns road distances where available.
  - **3a2**: Distance Service computes straight-line distances for missing targets.
  - **3a3**: Response includes mixed-mode distance indicators.
- **5a**: Property coordinates are missing or invalid
  - **5a1**: Distance Service cannot compute fallback.
  - **5a2**: Estimate API returns error HTTP 422 indicating invalid location reference.
- **5b**: Target amenity coordinates unavailable (missing school dataset)
  - **5b1**: Distance Service returns "missing dataset" error.
  - **5b2**: Valuation Engine skips that factor and reduces confidence score.
- **6a**: Straight-line fallback disabled by configuration
  - **6a1**: Distance Service returns failure to Estimate API.
  - **6a2**: Estimate API returns HTTP 503 or 424 indicating routing dependency unavailable.
- **7a**: Straight-line approximation produces unreasonable value (e.g., ocean crossing)
  - **7a1**: Distance Service caps maximum fallback distance.
  - **7a2**: Factor is excluded and marked as unreliable.

## Exception/Error Flows

- **5a**: Property coordinates are missing or invalid
  - **5a1**: Distance Service cannot compute fallback.
  - **5a2**: Estimate API returns error HTTP 422 indicating invalid location reference.
- **5b**: Target amenity coordinates unavailable (missing school dataset)
  - **5b1**: Distance Service returns "missing dataset" error.
  - **5b2**: Valuation Engine skips that factor and reduces confidence score.
- **6a**: Straight-line fallback disabled by configuration
  - **6a1**: Distance Service returns failure to Estimate API.
  - **6a2**: Estimate API returns HTTP 503 or 424 indicating routing dependency unavailable.
- **7a**: Straight-line approximation produces unreasonable value (e.g., ocean crossing)
  - **7a1**: Distance Service caps maximum fallback distance.
  - **7a2**: Factor is excluded and marked as unreliable.

## Data Involved

- Property coordinates
- Target amenity coordinates
- Road distance
- Straight-line distance
- Fallback flag
- Warning indicator
- Routing outage metrics
- Fallback usage count

## Requirements

### Functional Requirements

- **FR-01-001**: The Estimate API MUST request property distance computations with road distance preferred.
- **FR-01-002**: The Distance Service MUST query the routing provider for road distance before using fallback when routing is healthy.
- **FR-01-003**: The Distance Service MUST detect routing-provider timeouts or errors and mark road distance as unavailable.
- **FR-01-004**: The Distance Service MUST compute straight-line distance using property and target coordinates when routing fails and fallback is enabled.
- **FR-01-005**: The Distance Service MUST return the straight-line distance value to the Valuation Engine with a fallback flag.
- **FR-01-006**: The Valuation Engine MUST use straight-line distance for distance-based adjustments when fallback distance is returned.
- **FR-01-007**: The Estimate API MUST include a warning indicator in the response when routing fallback was used.
- **FR-01-008**: The Logging/Monitoring Service MUST record routing outage metrics and fallback usage count when routing fallback is used.
- **FR-01-009**: When the routing provider is healthy, the system MUST use road distances and return no fallback flag.
- **FR-01-010**: When the routing provider returns partial results, the Distance Service MUST return road distances where available and compute straight-line distances for missing targets.
- **FR-01-011**: Responses for partial routing failures MUST include mixed-mode distance indicators.
- **FR-01-012**: When property coordinates are missing or invalid, the Distance Service MUST not compute fallback distance.
- **FR-01-013**: When property coordinates are missing or invalid, the Estimate API MUST return HTTP 422 indicating an invalid location reference.
- **FR-01-014**: When target amenity coordinates are unavailable, the Distance Service MUST return a missing-dataset error.
- **FR-01-015**: When target amenity coordinates are unavailable, the Valuation Engine MUST skip the affected factor and reduce the confidence score.
- **FR-01-016**: When straight-line fallback is disabled by configuration and routing fails, the Distance Service MUST return failure to the Estimate API.
- **FR-01-017**: When straight-line fallback is disabled by configuration and routing fails, the Estimate API MUST return HTTP 503 with a controlled dependency error indicating the routing dependency is unavailable.
- **FR-01-018**: When straight-line fallback produces an unreasonable value, the Distance Service MUST first cap or otherwise adjust the fallback distance.
- **FR-01-019**: When straight-line fallback remains unreasonable after capping or adjustment, the affected factor MUST be excluded and marked as unreliable.
- **FR-01-020**: Successful fallback responses MUST indicate the fallback reason and the distance method used.
- **FR-01-021**: Successful fallback responses MUST allow the estimate request to complete successfully.
- **FR-01-022**: Successful fallback responses MUST reduce confidence relative to the normal routing-healthy case.
- **FR-01-023**: Fallback logs MUST include the routing failure cause.
- **FR-01-024**: Controlled dependency-error responses caused by disabled fallback MUST include a correlation ID.
- **FR-01-025**: Fallback logs MUST include a correlation ID.

### Non-Functional Requirements

- **NFR-001**: Routing failures MUST be observable through logs or metrics that distinguish outage conditions from normal distance computation.
- **NFR-002**: Fallback behavior MUST allow the estimate pipeline to continue whenever the use case permits a straight-line substitute.
- **NFR-003**: The feature implementation MUST remain within the project constraints of Python and vanilla HTML/CSS/JS.

### Key Entities

- **Distance Request**: A request from the Estimate API for property-to-target distance computation with road distance preferred.
- **Distance Result**: The returned distance value and related indicators showing whether road distance, straight-line fallback, or mixed-mode results were used.
- **Fallback Indicator**: Response metadata that signals fallback usage, the fallback reason, and the distance method used.
- **Routing Outage Record**: The log or metric record that captures routing failure cause and fallback usage counts.

## Traceability

### Acceptance Test to Functional Requirement Mapping

- **AT-UC27-001** -> FR-01-001, FR-01-002, FR-01-009
- **AT-UC27-002** -> FR-01-003, FR-01-004, FR-01-005, FR-01-007, FR-01-008, FR-01-020, FR-01-021, FR-01-022, FR-01-023
- **AT-UC27-003** -> FR-01-010, FR-01-011, FR-01-021
- **AT-UC27-004** -> FR-01-016, FR-01-017, FR-01-024
- **AT-UC27-005** -> FR-01-012, FR-01-013
- **AT-UC27-006** -> FR-01-008, FR-01-023, FR-01-025

### Flow Section to Functional Requirement Mapping

- **Main Success Scenario 1-2** -> FR-01-001, FR-01-002
- **Main Success Scenario 3-6** -> FR-01-003, FR-01-004, FR-01-005
- **Main Success Scenario 7-9** -> FR-01-006, FR-01-007, FR-01-008
- **Extension 3a** -> FR-01-010, FR-01-011
- **Extension 5a** -> FR-01-012, FR-01-013
- **Extension 5b** -> FR-01-014, FR-01-015
- **Extension 6a** -> FR-01-016, FR-01-017, FR-01-024
- **Extension 7a** -> FR-01-018, FR-01-019

## Assumptions

- Acceptance-test examples that mention specific response fields, warning text, and log fields are treated as valid examples of required externally visible behavior for this feature.
- The scenario narrative was not needed to derive additional requirements beyond the use case and acceptance tests.

## Dependencies

- Routing provider health and failure modes must be simulatable for acceptance testing.
- The Estimate API and Valuation Engine must exchange the fallback metadata referenced by the use case and acceptance tests.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In 100% of routing-healthy test runs, road distance is used and no fallback flag is returned.
- **SC-002**: In 100% of routing-timeout test runs with fallback enabled, the estimate completes successfully and the response identifies straight-line fallback usage.
- **SC-003**: In 100% of partial-routing-failure test runs, successful targets use road distance, failed targets use straight-line distance, and mixed-mode indicators are present.
- **SC-004**: In 100% of disabled-fallback and invalid-coordinate test runs, the system returns a controlled error outcome instead of silent degradation.
