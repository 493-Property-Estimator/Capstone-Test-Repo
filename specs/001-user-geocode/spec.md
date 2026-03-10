# Feature Specification: Enter Street Address to Estimate Property Value

**Feature Branch**: `001-user-geocode`  
**Created**: 2026-03-09  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-01.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-01-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-01-AT.md Hard rules: 1) Copy the use case flows directly into spec.md (main + alternate + exception flows). Preserve ordering and intent. Do not invent steps. 2) You may make style/grammar improvements only if meaning is unchanged. 3) Extract functional requirements (FRs) ONLY from: - the flows in use_cases-01.md, and - the checks/expectations in acceptance_tests-01.md. Do not add “nice-to-have” requirements that aren’t supported by those sources. 4) Keep implementation constraints: Python, vanilla HTML/CSS/JS. 5) Treat this use case as its own feature branch (branch naming suggestion is fine, but don’t actually run git commands unless asked). Spec contents required: - Feature name (from use case title) - Summary / goal - Actors - Preconditions - Triggers - Main flow (verbatim from use case) - Alternate flows (verbatim) - Exception/error flows (verbatim) - Data involved (only what the use case mentions) - Functional requirements list (numbered FR-01-001, FR-01-015, …) - Traceability section mapping: - each acceptance test → related FRs - each flow step (or flow section) → related FRs (coarse mapping is fine) Output: - Update/produce the spec.md for this feature. If Spec-Kit expects a per-feature folder/file, follow the tool’s convention, but the content must match the above constraints."

## Use Case Overview

**Summary / Goal**: Allow a general user to input a valid street address so the system can estimate the property value without requiring geographic coordinates.

**Actors**:
- Primary Actor: General User
- Secondary Actors: Geocoding Service

**Preconditions**:
- The Property Value Estimator system is operational.
- The geocoding service is available.
- The user has access to the estimate interface.

**Trigger**: The user selects the option to estimate a property value and chooses to enter a street address.

**Main Flow (verbatim)**:
1. The user selects the "Estimate Property Value" option.
2. The system prompts the user to enter a street address.
3. The user enters a street address.
4. The system validates the address format.
5. The system sends the address to the geocoding service.
6. The geocoding service returns geographic coordinates.
7. The system normalizes the location to a canonical location ID.
8. The system computes the property value estimate.
9. The system displays the estimated value and range to the user.

**Alternate Flows (verbatim)**:
- **4a**: Address format is invalid
  - 4a1: The system displays a validation error message.
  - 4a2: The user corrects the address and resumes at Step 3.
- **8a**: Required data for valuation is partially unavailable
  - 8a1: The system computes a partial estimate using available data.
  - 8a2: The system displays a warning indicating missing data.

**Exception / Error Flows (verbatim)**:
- **6a**: Geocoding service fails or returns no match
  - 6a1: The system informs the user that the address could not be found.
  - 6a2: The user may re-enter a different address (resume at Step 3).
  - 6a3: The use case ends in Failed End Condition.

**Data Involved (use case only)**:
- Street address input
- Address format validation result
- Geographic coordinates
- Canonical location ID
- Property value estimate
- Estimate range (low/high)
- Missing-data warning indicator

**Assumptions & Constraints**:
- Implementation uses Python with vanilla HTML, CSS, and JavaScript.
- Both a UI and an API are in scope for accepting street addresses and returning estimates.

## Clarifications

### Session 2026-03-09

- Q: Handling ambiguous/multiple address matches? → A: Present a disambiguation list for the user to choose the correct address.
- Q: Response time SLA for estimates? → A: p95 response time ≤ 5 seconds.
- Q: Handling repeated failed geocoding attempts? → A: 3 attempts max.
- Q: Validation error message content? → A: Must mention missing components (street number and street name).
- Q: Interface scope (UI vs API)? → A: Both UI and API.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Estimate by Street Address (Priority: P1)

A general user enters a valid street address and receives an estimated property value and range.

**Why this priority**: This is the primary entry method and most common flow.

**Independent Test**: Can be fully tested by submitting a valid address and verifying the estimate and range display.

**Acceptance Scenarios**:
1. **Given** the system is running and geocoding/valuation data are available, **When** the user submits a valid street address, **Then** the system displays a numeric estimate with a low/high range and no errors. (AT-01)
2. **Given** geocoding succeeds, **When** the system processes the geocoding result, **Then** a canonical location ID is produced and used for valuation. (AT-09)
3. **Given** valuation succeeds, **When** the system returns an estimate, **Then** low ≤ estimate ≤ high and all values are numeric and non-negative. (AT-10)

---

### User Story 2 - Correct Invalid Address (Priority: P2)

A user is told an address is invalid, fixes it, and then receives an estimate.

**Why this priority**: Invalid input is common and must be recoverable without blocking users.

**Independent Test**: Submit an invalid address, observe validation error, then correct and resubmit to receive estimate.

**Acceptance Scenarios**:
1. **Given** the system is running, **When** the user submits an invalid address format, **Then** the system shows a validation error and no estimate. (AT-02)
2. **Given** the user corrects the address and resubmits, **When** geocoding and valuation succeed, **Then** the estimate and range are displayed. (AT-03)

---

### User Story 3 - Handle Geocoding Failure or Partial Data (Priority: P3)

A user is informed when geocoding fails or when valuation data is partially unavailable, with appropriate recovery or warning.

**Why this priority**: External dependencies can fail; the system must provide clear outcomes and recovery options.

**Independent Test**: Simulate geocoding failure/no match and partial data to verify error messages, retries, and warnings.

**Acceptance Scenarios**:
1. **Given** geocoding returns no match, **When** the user submits a validly formatted address, **Then** the system indicates the address could not be found and allows re-entry without showing an estimate. (AT-04)
2. **Given** the geocoding service is down, **When** the user submits a valid address, **Then** the system indicates geocoding is unavailable and allows retry or re-entry without showing an estimate. (AT-05)
3. **Given** geocoding fails once and then succeeds, **When** the user retries, **Then** the estimate and range are displayed. (AT-06)
4. **Given** valuation data is partially unavailable, **When** the user submits a valid address, **Then** a partial estimate is shown with a missing-data warning. (AT-07)
5. **Given** the use case ends in failure, **When** the failure occurs, **Then** no estimate is shown and a reason with next step is provided. (AT-08)

### Edge Cases

- Invalid address format submitted (missing street number)
- Geocoding returns no match for a validly formatted address
- Geocoding returns multiple matches; user selects the correct address from a disambiguation list
- Geocoding service outage or timeout
- Repeated geocoding failures exceed 3 attempts and end in failure
- Required valuation data partially unavailable

## Requirements *(mandatory)*

### Functional Requirements

- **FR-01-001**: The system MUST allow the user to select the "Estimate Property Value" option. (Main Flow Step 1)
- **FR-01-002**: The system MUST prompt the user to enter a street address. (Main Flow Step 2)
- **FR-01-003**: The system MUST accept a user-entered street address for submission. (Main Flow Step 3)
- **FR-01-004**: The system MUST validate the address format before geocoding. (Main Flow Step 4)
- **FR-01-005**: When the address format is invalid, the system MUST display a user-actionable validation error message that mentions missing components (street number and street name) and MUST NOT call the geocoding service. (Extension 4a, AT-02)
- **FR-01-006**: After a validation error, the system MUST allow the user to correct the address and resubmit. (Extension 4a2, AT-03)
- **FR-01-007**: The system MUST send the address to the geocoding service when the format is valid. (Main Flow Step 5)
- **FR-01-008**: On geocoding success, the system MUST receive geographic coordinates and normalize the location to a canonical location ID. (Main Flow Steps 6-7, AT-09)
- **FR-01-009**: The system MUST compute a property value estimate after a canonical location ID is produced. (Main Flow Step 8)
- **FR-01-010**: The system MUST display a numeric estimate and low/high range when valuation succeeds. (Main Flow Step 9, AT-01)
- **FR-01-011**: The system MUST ensure Low ≤ Estimate ≤ High and all estimate values are numeric and non-negative. (AT-10)
- **FR-01-012**: When geocoding fails or returns no match, the system MUST inform the user that the address could not be found or that geocoding is unavailable, MUST NOT compute an estimate, and MUST allow re-entry or retry. (Extension 6a, AT-04, AT-05, AT-06)
- **FR-01-013**: When the use case ends in failure, the system MUST NOT display any estimate and MUST provide a failure reason with a user next step. (Failed End Condition, AT-08)
- **FR-01-014**: When required valuation data is partially unavailable, the system MUST compute a partial estimate and display a warning indicating missing data. (Extension 8a, AT-07)
- **FR-01-015**: The canonical location ID for identical addresses MUST be stable across repeated identical requests, assuming no underlying data changes. (AT-09)

### Traceability

**Acceptance Tests → Functional Requirements**:
- **AT-01** → FR-01-001, FR-01-002, FR-01-003, FR-01-004, FR-01-007, FR-01-008, FR-01-009, FR-01-010
- **AT-02** → FR-01-004, FR-01-005
- **AT-03** → FR-01-006, FR-01-007, FR-01-008, FR-01-009, FR-01-010
- **AT-04** → FR-01-012
- **AT-05** → FR-01-012
- **AT-06** → FR-01-012, FR-01-009, FR-01-010
- **AT-07** → FR-01-014, FR-01-010
- **AT-08** → FR-01-013
- **AT-09** → FR-01-008, FR-01-015
- **AT-10** → FR-01-011

**Flow Steps → Functional Requirements (coarse)**:
- **Main Flow Steps 1-3** → FR-01-001, FR-01-002, FR-01-003
- **Main Flow Step 4** → FR-01-004, FR-01-005, FR-01-006
- **Main Flow Steps 5-7** → FR-01-007, FR-01-008, FR-01-015
- **Main Flow Steps 8-9** → FR-01-009, FR-01-010, FR-01-011
- **Extension 4a** → FR-01-005, FR-01-006
- **Extension 6a** → FR-01-012, FR-01-013
- **Extension 8a** → FR-01-014

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid street-address submissions produce a numeric estimate and low/high range with no errors. (AT-01)
- **SC-002**: 100% of invalid address submissions show a user-actionable validation error and no estimate. (AT-02)
- **SC-003**: 100% of geocoding no-match or outage cases show a specific error and allow re-entry or retry without showing an estimate. (AT-04, AT-05, AT-06)
- **SC-004**: 100% of partial-data valuations display a missing-data warning alongside a partial estimate. (AT-07)
- **SC-005**: 100% of returned estimates satisfy Low ≤ Estimate ≤ High and all values are numeric and non-negative. (AT-10)
- **SC-006**: 95% of estimate requests complete within 5 seconds end-to-end. (AT-01)
