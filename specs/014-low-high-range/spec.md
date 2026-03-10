# Feature Specification: Return a Low/High Range

**Feature Branch**: `[014-low-high-range]`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description referencing `Use Cases/UC-14.md`, `Scenarios/UC-14-Scenarios.md`, and `Acceptance Tests/UC-14-AT.md`

## Overview

### Feature Name

Return a Low/High Range

### Summary / Goal

Enable the system to return a point estimate together with a low/high estimate range so a general user can understand uncertainty and avoid over-trusting a single number.

### Actors

- **Primary Actor**: General User
- **Secondary Actors**: Valuation Engine; Feature Store/Database; Assessment Data Store; Map UI

### Preconditions

- The preconditions for producing a point estimate are met (see UC-13).
- The valuation engine has a defined method to compute uncertainty (e.g., model interval, residual-based band, comparable variance).

### Trigger

The user requests an estimate and chooses to view, or the system automatically includes, an uncertainty range.

### Assumptions

- `Use Cases/UC-14.md` is the source of truth for flows, actors, preconditions, and trigger.
- `Acceptance Tests/UC-14-AT.md` is the source of truth for verifiable behavior and output checks.
- `Scenarios/UC-14-Scenarios.md` was used only to sharpen summary wording and user-story framing; no functional behavior was derived from it beyond the use case and acceptance tests.
- Graceful degradation to point estimate only is the default behavior when range computation fails or a reliable range cannot be computed, unless product configuration explicitly requires the request to fail.

### Implementation Constraints

- This feature must remain within the project's Python and vanilla HTML/CSS/JS constraints.

## Clarifications

### Session 2026-03-10

- Q: What product behavior applies when the system cannot compute the uncertainty range? → A: Always degrade gracefully by returning the point estimate with a range-unavailable warning.
- Q: How should the range interval level be defined? → A: Keep the interval level configurable and require API metadata and UI text to reflect the configured value.
- Q: How should the system handle ranges that are unreasonably wide? → A: Use a configurable maximum width limit and adjust or recompute the range when the limit is exceeded.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Estimate With Uncertainty Range (Priority: P1)

As a general user, I want to see a point estimate together with a low/high range so I can judge the estimate with uncertainty in mind.

**Why this priority**: Returning and clearly displaying the range is the primary user outcome of the feature.

**Independent Test**: Can be fully tested by requesting an estimate for a location where both point estimate and range are available and verifying the response fields, labels, metadata, and formatting.

**Acceptance Scenarios**:

1. **Given** a location where the system can produce both a point estimate and a range, **When** the estimate response is returned, **Then** the response contains exactly one point estimate, a low/high range, valid ordering around the estimate, and timestamp plus range metadata. (`AT-14-01`)
2. **Given** a returned range, **When** the UI renders the valuation result, **Then** the point estimate and range appear near each other, the range is clearly labeled as uncertainty, and the UI states that it is not a guaranteed bound. (`AT-14-02`)
3. **Given** returned range bounds, **When** the UI displays them, **Then** both bounds are currency-formatted using configured rounding rules and shown consistently in ascending order. (`AT-14-03`)
4. **Given** a configured range type or interval level, **When** an estimate returns a range, **Then** the response metadata and UI label/help text match that configuration without conflicting claims. (`AT-14-09`)

---

### User Story 2 - Keep the Point Estimate When Range Is Unavailable (Priority: P2)

As a general user, I want the point estimate to remain visible when a reliable range cannot be produced so I still receive useful output instead of a blank failure.

**Why this priority**: Graceful degradation protects the core estimation flow when range-specific issues occur.

**Independent Test**: Can be tested by forcing insufficient-data and internal-error conditions during range computation and verifying that the point estimate remains available with appropriate warnings when configured.

**Acceptance Scenarios**:

1. **Given** a request where a reliable range cannot be computed, **When** the system processes the request, **Then** the point estimate is returned, range fields are omitted or marked unavailable per convention, and the UI shows a non-blocking warning explaining that the range is unavailable. (`AT-14-04`)
2. **Given** an internal error while computing the range, **When** the system returns a response under graceful-degradation configuration, **Then** the point estimate remains displayed, the range is omitted or unavailable, and the UI offers a user-friendly warning and retry path. (`AT-14-05`)

---

### User Story 3 - Keep Range Output Valid and Transparent (Priority: P3)

As a general user, I want invalid or low-confidence ranges to be corrected and explained so I can trust what the UI shows without mistaking it for certainty.

**Why this priority**: Guardrails, repeatability, and reduced-reliability warnings are important trust protections after the core range flow exists.

**Independent Test**: Can be tested by forcing invalid-range and partial-feature conditions, then repeating the same input under fixed versions to verify warnings, guardrails, and consistent outputs.

**Acceptance Scenarios**:

1. **Given** a case that would produce an invalid or unstable range, **When** the system computes the range, **Then** the returned bounds satisfy validity constraints and any adjustment is surfaced with a non-blocking warning. (`AT-14-06`)
2. **Given** some feature sources are unavailable, **When** the system returns the estimate, **Then** it either returns point estimate plus range with a reduced-reliability warning or point estimate only with a range-unavailable warning, without implying missing features are zero-valued. (`AT-14-07`)
3. **Given** repeated requests with the same input and unchanged datasets and configuration, **When** results are returned, **Then** the point estimate, range, and any warnings stay consistent within configured rounding rules. (`AT-14-08`)

### Edge Cases

- The system cannot compute a reliable range because too many features are missing or baseline data is missing beyond the allowed threshold.
- Range computation fails due to an internal error after the point estimate has been computed.
- The computed range would be invalid because the low bound is greater than the high bound, the low bound is negative, or the range is unreasonably wide.
- Some feature sources are unavailable, so the system must decide whether to return a range with reduced-reliability warning or omit the range.
- The same request is repeated while dataset versions and model or range configuration remain unchanged.

## Requirements *(mandatory)*

### Main Flow

1. The user submits a property estimate request.
2. The system computes the point estimate (as in UC-13).
3. The valuation engine computes an uncertainty measure for the estimate using the configured approach (e.g., prediction interval or percentile band).
4. The system converts the uncertainty measure into a low/high range and applies formatting rules (currency, rounding, ordering).
5. The system returns a response containing the point estimate and the low/high range, along with minimal metadata describing the range type (e.g., “confidence band”).
6. The UI displays the range near the point estimate and labels it clearly as a range, not a guaranteed bound.

### Alternate Flows

- **3a**: Insufficient data to compute a range (too many missing features; baseline missing beyond allowed threshold)
  - **3a1**: The system returns only the point estimate and flags that a range cannot be computed reliably.
  - **3a2**: The UI displays a warning and suggests adding more property details (if supported) to improve reliability.
- **3b**: Range computation fails due to internal error
  - **3b1**: The system logs the error and returns only the point estimate (preferred) or a failure response (if range is mandatory).

### Exception/Error Flows

- **4a**: The computed range is invalid (low > high, negative low, unreasonably wide)
  - **4a1**: The system clamps and/or recomputes using a safe fallback band.
  - **4a2**: The system flags the response with a “range adjusted” warning for transparency.

### Data Involved

- **Property estimate request**: The user request that triggers point-estimate and range processing.
- **Point estimate**: The estimated property value computed as in UC-13.
- **Uncertainty measure**: The uncertainty output computed by the valuation engine using the configured approach.
- **Low estimate**: The lower bound of the returned estimate range.
- **High estimate**: The upper bound of the returned estimate range.
- **Range type metadata**: Minimal metadata describing the type of range, such as a confidence band or interval label.
- **Timestamp**: The timestamp associated with the returned estimate and range.
- **Warning flags**: Non-blocking warnings such as range unavailable, reduced reliability, or range adjusted.
- **Property details**: Additional property details the UI may suggest adding if supported when reliability is low.

### Functional Requirements

- **FR-01-001**: The system MUST allow the user to request an estimate that includes an uncertainty range, whether the user explicitly chooses to view it or the system includes it automatically.
- **FR-01-002**: The system MUST compute the point estimate as in UC-13 before range processing continues.
- **FR-01-003**: The valuation engine MUST compute an uncertainty measure for the estimate using the configured approach.
- **FR-01-004**: The system MUST convert the uncertainty measure into `low_estimate` and `high_estimate` values and apply currency, rounding, and ordering rules to the range.
- **FR-01-005**: For a successful range response, the system MUST return exactly one point estimate together with `low_estimate`, `high_estimate`, timestamp, and minimal metadata describing the range type.
- **FR-01-006**: For a successful range response, the returned values MUST satisfy `low_estimate` ≤ `estimated_value` ≤ `high_estimate`.
- **FR-01-007**: The UI MUST display the point estimate and low/high range near each other and label the range clearly as an estimate range or uncertainty band rather than a guaranteed bound.
- **FR-01-008**: The UI MUST include brief disclaimer or help text indicating that the returned range is not a guaranteed bound.
- **FR-01-009**: The UI MUST format both range bounds as local currency using the configured rounding rules and display them in ascending order consistently across views.
- **FR-01-010**: If insufficient data prevents reliable range computation, the system MUST return only the point estimate, omit the range or mark it unavailable per response convention, include a warning explaining why the range is unavailable, and the UI MUST display a non-blocking notice.
- **FR-01-011**: If range computation fails due to internal error, the system MUST log the error, return the point estimate without a range, surface a user-friendly warning that the range is temporarily unavailable, and provide a retry path.
- **FR-01-012**: If the computed range is invalid because the low bound exceeds the high bound, the low bound is negative, or the range exceeds the configured maximum width limit, the system MUST clamp and/or recompute using a safe fallback band so the returned range satisfies basic validity constraints.
- **FR-01-013**: If a guardrail adjustment or fallback band is applied to the range, the system MUST include a non-blocking “range adjusted” warning in the response and the UI MUST surface that warning.
- **FR-01-014**: If some feature sources are unavailable, the system MUST either return the point estimate and range with a reduced-reliability warning or return the point estimate only with a range-unavailable warning, and the UI MUST NOT imply that missing features are zero-valued.
- **FR-01-015**: For repeated requests with the same input while dataset versions and model or range configuration are unchanged, the system MUST return consistent point estimate and range outputs within configured rounding rules, and any warnings present for the same conditions MUST remain consistent.
- **FR-01-016**: When the system is configured to use a specific range type or interval level, the response metadata MUST identify that configured range type or level and the UI label or help text MUST match that configuration without conflicting interval claims.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-14-01 | FR-01-001, FR-01-002, FR-01-003, FR-01-004, FR-01-005, FR-01-006 |
| AT-14-02 | FR-01-007, FR-01-008 |
| AT-14-03 | FR-01-004, FR-01-009 |
| AT-14-04 | FR-01-010 |
| AT-14-05 | FR-01-011 |
| AT-14-06 | FR-01-012, FR-01-013 |
| AT-14-07 | FR-01-010, FR-01-014 |
| AT-14-08 | FR-01-015 |
| AT-14-09 | FR-01-005, FR-01-016 |

#### Flow Steps or Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow Step 1 | FR-01-001 |
| Main Flow Step 2 | FR-01-002 |
| Main Flow Step 3 | FR-01-003, FR-01-010, FR-01-011 |
| Main Flow Step 4 | FR-01-004, FR-01-009, FR-01-012, FR-01-013 |
| Main Flow Step 5 | FR-01-005, FR-01-006, FR-01-016 |
| Main Flow Step 6 | FR-01-007, FR-01-008 |
| Alternate Flow 3a | FR-01-010, FR-01-014 |
| Alternate Flow 3b | FR-01-011 |
| Exception Flow 4a | FR-01-012, FR-01-013 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of successful range-enabled test runs, the system returns one point estimate plus one low/high range with timestamp and range metadata, and the UI displays them together with clear uncertainty labeling.
- **SC-002**: In 100% of range-display test runs, the UI communicates that the range is not a guaranteed bound and shows range values in local currency, ascending order, and consistent formatting across views.
- **SC-003**: In 100% of insufficient-data or internal-error test runs where graceful degradation is configured, the point estimate remains visible, the unavailable range is explicitly warned about, and the UI provides a non-blocking message.
- **SC-004**: Under normal load, at least 95% of successful estimate requests that include range computation for locations with cached features complete within 3.5 seconds.
- **SC-005**: In 100% of repeated-request test runs with unchanged input, dataset versions, and model or range configuration, the point estimate, range, and warning behavior remain consistent within configured rounding rules.
