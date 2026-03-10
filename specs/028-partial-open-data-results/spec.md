# Feature Specification: Provide Partial Results When Some Open Data is Unavailable

**Feature Branch**: `028-partial-open-data-results`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-28.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-28-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-28-AT.md Hard rules: 1) Copy the use case flows directly into spec.md (main + alternate + exception flows). Preserve ordering and intent. Do not invent steps. 2) You may make style/grammar improvements only if meaning is unchanged. 3) Extract functional requirements (FRs) ONLY from: - the flows in UC-28.md, and - the checks/expectations in UC-28-AT.md Do not add nice-to-have requirements that are not supported by those sources. 4) Keep implementation constraints: Python, vanilla HTML/CSS/JS. 5) Treat this use case as its own feature branch (branch naming suggestion is fine, but do not actually run git commands unless asked). Spec contents required: - Feature name (from use case title) - Summary / goal - Actors - Preconditions - Triggers - Main flow (verbatim from use case) - Alternate flows (verbatim) - Exception/error flows (verbatim) - Data involved (only what the use case mentions) - Functional requirements list (numbered FR-01-001, FR-01-015, ...) - Traceability section mapping: - each acceptance test to related FRs - each flow step (or flow section) to related FRs (coarse mapping is fine) Output: - Update/produce the spec.md for this feature. If Spec-Kit expects a per-feature folder/file, follow the tool’s convention, but the content must match the above constraints."

## Summary

A user must receive a usable property estimate even if some open-data sources are missing or temporarily unavailable. The system must compute the estimate using whatever factors are available and return completeness and confidence indicators instead of failing the entire estimate whenever a partial result is still possible.

## Clarifications

### Session 2026-03-10

- Q: Which HTTP status should be used when too many factors are missing but a low-reliability estimate is still returned? → A: Always return HTTP 200 with a high-severity warning.
- Q: Which HTTP status should be used when the baseline assessment value is missing? → A: Always return HTTP 424.
- Q: Is strict mode supported and in scope for this feature? → A: Yes, strict mode is supported and in scope.

## Actors

- Primary actor: General User
- Secondary actors: Open Data Source Feeds, Feature Store, Valuation Engine, Logging/Monitoring

## Preconditions

- Property location is resolvable.
- Baseline tax assessment value is available.
- At least one supporting feature dataset is available (e.g., comparables).

## Triggers

- User requests an estimate and one or more required data dependencies fail during processing.

## Implementation Constraints

- The feature must fit the existing project constraints of Python and vanilla HTML/CSS/JS.

## User Scenarios & Testing

### User Story 1 - Get a usable estimate with partial open-data coverage (Priority: P1)

As a user requesting a property estimate, I need the system to return a usable estimate with missing-factor warnings and reduced confidence when one or more optional datasets are unavailable.

**Why this priority**: This is the core outcome of UC-28 and the primary protection against unnecessary total estimate failures.

**Independent Test**: Can be fully tested by requesting estimates with one optional dataset unavailable and verifying that the API returns a successful partial result with estimate values, confidence, completeness, missing-factor details, warnings, and factor breakdown.

**Acceptance Scenarios**:

1. **Given** baseline assessment data and all but one optional dataset are available, **When** the user requests an estimate, **Then** the API returns HTTP 200 with the estimate, reduced confidence, completeness information, missing factors, warnings, and a factor breakdown showing computed and missing factors.
2. **Given** the crime dataset is unavailable, **When** the user requests an estimate, **Then** the crime adjustment factor is omitted and the response includes a missing-factor warning for crime statistics.

---

### User Story 2 - Continue with reduced reliability when key supporting datasets are missing (Priority: P2)

As a user, I need the estimate pipeline to continue with explicit low-reliability signaling when important supporting data is missing or repeatedly times out, so I can still receive a result when partial computation remains possible.

**Why this priority**: UC-28 explicitly requires low-confidence partial estimates, reliability threshold handling, and bounded timeout strategies.

**Independent Test**: Can be tested by disabling comparables or multiple datasets and by simulating timeouts, then verifying low-confidence or low-reliability responses, omission of unavailable factors, timeout handling, and completed requests.

**Acceptance Scenarios**:

1. **Given** comparables are unavailable, **When** the user requests an estimate, **Then** the system still returns an estimate based on baseline with very low confidence unless comparables are treated as critical.
2. **Given** multiple datasets are missing, **When** the user requests an estimate, **Then** the response indicates low reliability, lists missing factors, and does not silently succeed without reliability signaling.
3. **Given** an open-data source times out, **When** the user requests an estimate, **Then** the system performs bounded retry or uses a cached snapshot and, if the dataset is still unavailable, omits the factor, flags it, and completes the request.

---

### User Story 3 - Fail explicitly when a required condition prevents a partial estimate (Priority: P3)

As a user, I need explicit failure responses when baseline data is missing or strict requirements cannot be met, so I know why the estimate cannot be produced.

**Why this priority**: The use case and acceptance tests require controlled failure for missing baseline data and strict-mode requests.

**Independent Test**: Can be tested by removing the baseline or requesting strict mode with a required missing factor, then verifying an error response that identifies the blocking condition.

**Acceptance Scenarios**:

1. **Given** the baseline assessment value is missing, **When** the user requests an estimate, **Then** the API returns a controlled failure indicating the baseline is required.
2. **Given** strict mode is supported and a required factor is unavailable, **When** the user requests an estimate in strict mode, **Then** the API returns an error identifying the unavailable required factor and listing the missing required datasets.

### Edge Cases

- The baseline assessment value is missing.
- The crime dataset is unavailable.
- Comparable property data is unavailable.
- Too many factors are missing and reliability drops below the minimum threshold.
- An open-data source times out temporarily.
- Strict mode requires a factor that is unavailable.

## Main Flow

## Main Success Scenario

1. **User** selects a property and requests an estimate.
2. **Estimate API** validates the request and resolves property location.
3. **Estimate API** retrieves baseline assessment value.
4. **Estimate API** attempts to retrieve all relevant open-data features (crime, green spaces, schools, stores, work areas).
5. **System** detects that one or more datasets are unavailable or missing for this region.
6. **Valuation Engine** identifies which factors can be computed and which must be skipped.
7. **Valuation Engine** computes the estimate using available factors and aggregates them using configured statistics.
8. **Valuation Engine** generates a completeness score based on missing factors and data freshness.
9. **Estimate API** returns the final estimate, baseline value, factor breakdown, missing-data list, and confidence score.
10. **UI** displays estimate with warning indicators.

## Alternate Flows

## Extensions

- **5a**: Critical dataset missing (baseline assessment value missing)
  - **5a1**: Estimate API cannot compute final value.
  - **5a2**: API returns HTTP 424/422 indicating baseline is required.
- **5b**: Crime dataset unavailable
  - **5b1**: Crime adjustment factor omitted.
  - **5b2**: Response includes missing factor warning.
- **5c**: Comparable property dataset unavailable
  - **5c1**: Valuation engine uses baseline value with minimal adjustments.
  - **5c2**: Confidence score becomes very low.
  - **5c3**: UI displays "Estimate is low confidence due to lack of comparable properties."
- **6a**: Too many factors missing (below minimum threshold)
  - **6a1**: Valuation engine returns "estimate not reliable" status.
  - **6a2**: Estimate API may return HTTP 206 Partial Content or HTTP 200 with warning severity HIGH.
- **4a**: Open-data source times out temporarily
  - **4a1**: System retries request once or uses cached last-known value.
  - **4a2**: If still unavailable, system proceeds without it.
- **7a**: User requested strict mode (must include certain factors)
  - **7a1**: Estimate API returns HTTP 424 indicating requested factor unavailable.
  - **7a2**: Response lists missing required datasets.

## Exception/Error Flows

- **5a**: Critical dataset missing (baseline assessment value missing)
  - **5a1**: Estimate API cannot compute final value.
  - **5a2**: API returns HTTP 424/422 indicating baseline is required.
- **6a**: Too many factors missing (below minimum threshold)
  - **6a1**: Valuation engine returns "estimate not reliable" status.
  - **6a2**: Estimate API may return HTTP 206 Partial Content or HTTP 200 with warning severity HIGH.
- **7a**: User requested strict mode (must include certain factors)
  - **7a1**: Estimate API returns HTTP 424 indicating requested factor unavailable.
  - **7a2**: Response lists missing required datasets.

## Data Involved

- Property location
- Baseline assessment value
- Open-data features for crime, green spaces, schools, stores, and work areas
- Factor breakdown
- Missing-data list
- Confidence score
- Completeness score
- Data freshness

## Requirements

### Functional Requirements

- **FR-01-001**: The system MUST allow the user to request an estimate for a selected property.
- **FR-01-002**: The Estimate API MUST validate the request and resolve the property location.
- **FR-01-003**: The Estimate API MUST retrieve the baseline assessment value before computing the estimate.
- **FR-01-004**: The Estimate API MUST attempt to retrieve all relevant open-data features for crime, green spaces, schools, stores, and work areas.
- **FR-01-005**: The system MUST detect when one or more datasets are unavailable or missing for the region.
- **FR-01-006**: The Valuation Engine MUST identify which factors can be computed and which must be skipped.
- **FR-01-007**: The Valuation Engine MUST compute the estimate using the available factors and configured statistics.
- **FR-01-008**: The Valuation Engine MUST generate a completeness score based on missing factors and data freshness.
- **FR-01-009**: The Estimate API MUST return the final estimate, baseline value, factor breakdown, missing-data list, and confidence score for partial results.
- **FR-01-010**: The UI MUST display the estimate with warning indicators.
- **FR-01-011**: When the crime dataset is unavailable, the system MUST omit the crime adjustment factor and include a missing-factor warning in the response.
- **FR-01-012**: When the comparable property dataset is unavailable, the Valuation Engine MUST use the baseline value with minimal adjustments.
- **FR-01-013**: When the comparable property dataset is unavailable, the confidence score MUST become very low.
- **FR-01-014**: When too many factors are missing, the Valuation Engine MUST return an "estimate not reliable" status.
- **FR-01-015**: Partial-result responses with one optional dataset missing MUST return HTTP 200.
- **FR-01-016**: Partial-result responses MUST include missing factors, warnings, completeness information, and a factor breakdown showing computed and missing factors.
- **FR-01-017**: When the baseline assessment value is missing, the Estimate API MUST return HTTP 424 with a controlled failure indicating that the baseline is required.
- **FR-01-018**: When an open-data source times out temporarily, the system MUST retry the request once or use a cached last-known value.
- **FR-01-019**: If a timed-out dataset remains unavailable after timeout handling, the system MUST proceed without that dataset, omit the related factor, and flag it in the response.
- **FR-01-020**: Estimate requests affected by temporary dataset timeouts MUST still complete.
- **FR-01-021**: The feature MUST support strict mode requests that require specified factors to be available before an estimate can be returned.
- **FR-01-022**: When strict mode requires a factor that is unavailable, the Estimate API MUST return HTTP 424 indicating that the requested factor is unavailable.
- **FR-01-026**: When strict mode requires a factor that is unavailable, the response MUST list the missing required datasets.
- **FR-01-023**: When multiple datasets are missing beyond the minimum reliability threshold, the response MUST return HTTP 200, indicate low reliability with a high-severity warning, and list missing factors rather than silently succeeding.
- **FR-01-024**: When a partial result is returned with one missing optional dataset, the response MUST include the baseline value, estimated value, confidence, completeness, missing factors, and warnings.
- **FR-01-025**: When a critical dataset prevents estimate computation, the API MUST fail the estimate request instead of returning a partial estimate.

### Non-Functional Requirements

- **NFR-001**: The system MUST continue producing usable partial estimates whenever the use case allows one or more factors to be skipped safely.
- **NFR-002**: Partial-result responses MUST communicate reduced completeness and confidence clearly enough for users to understand that the estimate was computed with missing data.
- **NFR-003**: The feature implementation MUST remain within the project constraints of Python and vanilla HTML/CSS/JS.

### Key Entities

- **Estimate Request**: The user's request for a property estimate, including the selected property and any strict-mode requirement.
- **Estimate Result**: The returned estimate output containing baseline value, estimated value, factor breakdown, missing-data list, confidence score, completeness score, and warning information.
- **Dataset Availability State**: The availability, timeout, or missing state for each open-data source used during estimate computation.
- **Reliability Status**: The valuation result state indicating whether the estimate is usable, low confidence, or not reliable.

## Traceability

### Acceptance Test to Functional Requirement Mapping

- **AT-UC28-001** -> FR-01-009, FR-01-011, FR-01-015, FR-01-016, FR-01-024
- **AT-UC28-002** -> FR-01-012, FR-01-013, FR-01-016
- **AT-UC28-003** -> FR-01-014, FR-01-023
- **AT-UC28-004** -> FR-01-017, FR-01-025
- **AT-UC28-005** -> FR-01-018, FR-01-019, FR-01-020
- **AT-UC28-006** -> FR-01-021, FR-01-022, FR-01-026

### Flow Section to Functional Requirement Mapping

- **Main Success Scenario 1-4** -> FR-01-001, FR-01-002, FR-01-003, FR-01-004
- **Main Success Scenario 5-8** -> FR-01-005, FR-01-006, FR-01-007, FR-01-008
- **Main Success Scenario 9-10** -> FR-01-009, FR-01-010
- **Extension 5a** -> FR-01-017, FR-01-025
- **Extension 5b** -> FR-01-011
- **Extension 5c** -> FR-01-012, FR-01-013
- **Extension 6a** -> FR-01-014, FR-01-023
- **Extension 4a** -> FR-01-018, FR-01-019, FR-01-020
- **Extension 7a** -> FR-01-021, FR-01-022, FR-01-026

## Assumptions

- Acceptance-test examples that mention specific response fields and values are treated as valid examples of required externally visible behavior for this feature.
- The scenario narrative was not needed to derive additional requirements beyond the use case and acceptance tests.

## Dependencies

- Open-data sources and the feature store must be controllable for outage and timeout simulation during testing.
- The Estimate API, Valuation Engine, and UI warning surface must exchange the partial-result metadata referenced by the use case and acceptance tests.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In 100% of one-missing-dataset test runs, the system returns a successful partial estimate with missing-factor details, warnings, and reduced confidence.
- **SC-002**: In 100% of comparables-missing test runs where partial estimates are still permitted, the system returns an estimate with very low confidence instead of failing silently.
- **SC-003**: In 100% of timeout test runs, the request completes after bounded retry, cached fallback, or omission of the unavailable factor.
- **SC-004**: In 100% of baseline-missing or strict-mode-blocked test runs, the system returns an explicit failure identifying the blocking requirement.
