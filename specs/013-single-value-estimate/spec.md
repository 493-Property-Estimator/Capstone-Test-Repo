# Feature Specification: Return a Single Estimated Value

**Feature Branch**: `[013-single-value-estimate]`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description referencing `Use Cases/UC-13.md`, `Scenarios/UC-13-Scenarios.md`, and `Acceptance Tests/UC-13-AT.md`

## Overview

### Feature Name

Return a Single Estimated Value

### Summary / Goal

Enable a general user to submit a property location, optionally include basic attributes, and receive one clear estimated property value for quick interpretation and comparison.

### Actors

- **Primary Actor**: General User
- **Secondary Actors**: Map UI; Geocoding/Normalization Service; Valuation Engine; Feature Store/Database; Open-Data Ingestion Pipeline (offline); Assessment Data Store

### Preconditions

- The PVE system is available (UI and/or API reachable).
- The user has provided a property location (address, lat/long, or map click) that can be normalized to a canonical location.
- Required baseline datasets (e.g., tax assessment baseline) have been ingested and are queryable, or the system has a defined fallback behavior for missing baseline.

### Trigger

The user submits a request to estimate a property value (e.g., clicks "Estimate" in the UI).

### Assumptions

- `Use Cases/UC-13.md` is the source of truth for flows, actors, preconditions, and trigger.
- `Acceptance Tests/UC-13-AT.md` is the source of truth for verifiable behavior and output checks.
- `Scenarios/UC-13-Scenarios.md` was used only to sharpen summary wording and user-story framing; no functional behavior was derived from it beyond the use case and acceptance tests.

### Implementation Constraints

- This feature must remain within the project's Python and vanilla HTML/CSS/JS constraints.

## Clarifications

### Session 2026-03-10

- Q: Which baseline fallback policy applies when the normalized location has no assessment baseline? → A: Use nearest-neighbour baseline and return an estimate with a missing-baseline warning.
- Q: How must request tracing be exposed for successful estimate requests? → A: Support either returning the identifier in the response or logging one tied to the client session.
- Q: When parcel association and clicked point differ, which source defines the canonical location? → A: Use the parcel-associated location as the authoritative canonical location.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get One Clear Estimate (Priority: P1)

As a general user, I want to submit a property location and receive one clear estimated value so I can quickly judge and compare a property.

**Why this priority**: This is the primary value of the feature and the main success path described by the use case.

**Independent Test**: Can be fully tested by submitting a valid location with available baseline and feature data and verifying that exactly one estimate, timestamp, and location summary are returned and displayed.

**Acceptance Scenarios**:

1. **Given** a valid location with available baseline and feature data, **When** the user submits an estimate request, **Then** the system returns exactly one estimated value with timestamp, location summary, and baseline metadata when available, and the UI displays the single value prominently. (`AT-13-01`)
2. **Given** a valid location and valid optional attributes, **When** the user submits an estimate request, **Then** the request is accepted, one estimated value is returned, and the UI preserves the entered attributes after showing the result. (`AT-13-02`)
3. **Given** a returned estimate, **When** the UI displays the result, **Then** the value is shown as local currency with configured rounding and without conflicting formats across views. (`AT-13-09`)

---

### User Story 2 - Correct Input Problems Before Estimation (Priority: P2)

As a general user, I want actionable feedback when my location or attributes are invalid so I can correct the request and try again without losing my work.

**Why this priority**: Validation and location disambiguation directly control whether the user can reach the core estimate outcome.

**Independent Test**: Can be tested by submitting invalid, ambiguous, and unresolvable inputs and verifying that the system blocks estimation, explains the issue, and preserves the user's ability to correct and resubmit.

**Acceptance Scenarios**:

1. **Given** an empty location, invalid coordinates, or invalid numeric attributes, **When** the user submits an estimate request, **Then** the system returns structured validation errors, the UI highlights the invalid inputs, and no estimate is displayed while preserving entered data for correction. (`AT-13-03`)
2. **Given** an ambiguous address, **When** the system attempts to normalize it, **Then** the UI presents candidate matches or another disambiguation method and does not produce an estimate until a specific location is chosen. (`AT-13-04`)
3. **Given** an unresolvable address, **When** the user submits an estimate request, **Then** the UI shows a clear failure state with a retry path and does not show a stale estimate for that address. (`AT-13-05`)

---

### User Story 3 - Continue Transparently Through Fallbacks and Failures (Priority: P3)

As a general user, I want the estimate flow to handle missing data and service failures transparently so I understand whether the result is usable and when I need to retry.

**Why this priority**: These behaviors protect trust in the estimate, but they build on the primary request flow and input handling.

**Independent Test**: Can be tested by simulating missing baseline data, partial feature availability, valuation-engine failure, and repeated identical requests with fixed data versions.

**Acceptance Scenarios**:

1. **Given** no baseline assessment is available and fallback policy allows estimation, **When** the user submits an estimate request, **Then** one estimate is returned and a non-blocking missing-baseline warning is surfaced. (`AT-13-06`)
2. **Given** one or more feature sources are unavailable or time out, **When** the user submits an estimate request, **Then** the system may estimate using available features, surfaces a completeness warning, and does not imply missing features are zero-valued. (`AT-13-07`)
3. **Given** the valuation engine fails, **When** the system processes the request, **Then** no estimate is displayed and the UI presents a user-friendly retry path. (`AT-13-08`)
4. **Given** the same request is submitted multiple times with unchanged data versions, baseline data, and model version, **When** results are returned, **Then** the estimate and metadata remain consistent within the configured rounding rule. (`AT-13-10`, `AT-13-11`)

### Edge Cases

- The user submits an empty address, invalid coordinates, or invalid numeric attributes.
- The entered address is ambiguous and needs disambiguation before normalization can complete.
- The entered address cannot be normalized and a previous estimate must not remain visible as if it applies to the failed request.
- Assessment baseline data is missing for the normalized location.
- One or more feature sources are unavailable or time out during estimation.
- The valuation engine fails after request validation succeeds.
- The same request is repeated after no underlying data version changes.

## Requirements *(mandatory)*

### Main Flow

1. The user enters a property location (address, coordinates, or map click) and optionally provides basic attributes (e.g., size, beds, baths).
2. The user submits the request to get an estimate.
3. The system validates the request (required fields present; coordinates in valid ranges; address not empty).
4. The system normalizes the input to a canonical location ID and resolves a representative point/geometry for feature computation.
5. The system retrieves the assessment baseline value for the canonical location (or nearest applicable parcel/assessment unit) and records the baseline metadata (assessment year, source).
6. The system retrieves and/or computes relevant open-data features for the location (e.g., proximity to amenities, green space, school distance, commute accessibility, crime signals when available).
7. The valuation engine computes an estimated value using the assessment baseline plus factor adjustments derived from the available features.
8. The system formats the estimated value for display (currency, rounding rules) and prepares the response payload (estimate, location summary, timestamp, baseline metadata).
9. The system returns the single estimated value to the UI/API client.
10. The UI displays the single estimated value prominently for quick interpretation.

### Alternate Flows

- **5a**: Assessment baseline not found for the normalized location
  - **5a1**: The system applies the defined fallback (e.g., nearest-neighbour assessment baseline, neighbourhood median baseline, or "baseline unavailable" mode).
  - **5a2**: The system marks the response with a missing-baseline warning for transparency.
- **6a**: Some open-data features are unavailable (missing dataset, compute timeout, routing unavailable)
  - **6a1**: The system proceeds with partial feature set and computes an estimate with reduced confidence.
  - **6a2**: The system flags the missing features and returns a warning that the estimate may be less reliable.

### Exception/Error Flows

- **3a**: Request validation fails (invalid coordinates, empty address, unsupported geometry)
  - **3a1**: The system returns a structured validation error describing the invalid field(s) and how to correct them.
  - **3a2**: The UI highlights the invalid input and does not run valuation.
- **4a**: Location cannot be normalized (address not found / ambiguous / geocoding failure)
  - **4a1**: The system prompts the user to refine the address or select from suggested matches.
  - **4a2**: If a map UI is available, the system invites the user to click the correct location.
- **7a**: Valuation engine fails (internal error)
  - **7a1**: The system logs the error with correlation IDs and returns a user-friendly message indicating the estimate could not be produced.

### Data Involved

- **Property location**: Address, coordinates, or map click supplied by the user.
- **Basic attributes**: Optional property details such as size, beds, and baths.
- **Canonical location ID**: The normalized location identifier used for downstream retrieval and computation.
- **Parcel-associated canonical location**: The authoritative canonical location used when a clicked point and parcel association differ.
- **Representative point/geometry**: The resolved spatial reference used for feature computation.
- **Assessment baseline value**: The baseline value retrieved for the canonical location or nearest applicable parcel/assessment unit.
- **Baseline metadata**: Assessment year and source associated with the baseline value.
- **Open-data features**: Relevant location-derived features such as proximity, green space, school distance, commute accessibility, and crime signals when available.
- **Estimated value**: The single numeric property-value estimate returned to the user.
- **Location summary**: The normalized address and/or coordinates included with the result.
- **Timestamp**: The time when the estimate was produced.
- **Warnings**: Transparency flags for missing baseline data or incomplete feature coverage.
- **Correlation/request identifier**: The tracing identifier used to connect the request to logs or the client session.

### Functional Requirements

- **FR-01-001**: The system MUST allow the user to provide a property location using an address, coordinates, or map click and MAY accept optional basic attributes such as size, beds, and baths.
- **FR-01-002**: The system MUST allow the user to submit an estimate request for the provided location.
- **FR-01-003**: The system MUST validate that required request fields are present, coordinates are within valid ranges, and the address is not empty before valuation proceeds.
- **FR-01-004**: The system MUST normalize the submitted location to a canonical location ID and resolve a representative point or geometry for feature computation, using the parcel-associated location as the authoritative canonical location when a clicked point and parcel association differ.
- **FR-01-005**: The system MUST retrieve the assessment baseline value for the canonical location or nearest applicable parcel or assessment unit and record baseline metadata including assessment year and source.
- **FR-01-006**: The system MUST retrieve and/or compute the relevant open-data features available for the normalized location.
- **FR-01-007**: The valuation engine MUST compute one estimated value using the assessment baseline plus factor adjustments derived from the available features.
- **FR-01-008**: The system MUST format the estimated value as local currency using the configured rounding rule and prepare a response payload containing the estimate, location summary, timestamp, and baseline metadata when available.
- **FR-01-009**: For a successful request, the system MUST return exactly one `estimated_value` to the UI or API client.
- **FR-01-010**: The UI MUST display the returned single estimated value prominently and MUST NOT present it as a range or as multiple competing values.
- **FR-01-011**: The successful response MUST include a timestamp for when the estimate was produced and a location summary containing the normalized address and/or coordinates.
- **FR-01-012**: The successful response MUST include baseline metadata when that metadata is available.
- **FR-01-013**: The system MUST accept valid optional attributes without preventing estimation, and the UI MUST preserve those entered attributes after the estimate is shown so the user can adjust and re-run the request.
- **FR-01-014**: If request validation fails, the system MUST return a structured validation error identifying the invalid field or fields and how to correct them, the UI MUST highlight the invalid input or inputs, the system MUST NOT run valuation or display an estimated value, and the user MUST be able to correct the inputs and resubmit without losing all entered data.
- **FR-01-015**: If a location cannot be normalized because the address is ambiguous or not found, the system MUST prompt the user to refine the address or select from suggested matches and, when a map UI is available, MUST allow the user to choose the correct location by map click before any estimate is produced.
- **FR-01-016**: If an address cannot be resolved for the submitted request, the UI MUST display a clear user-friendly failure state with a retry path, and the system MUST NOT display a stale or previous estimate as if it applies to that address.
- **FR-01-017**: If the assessment baseline is not found for the normalized location, the system MUST apply the nearest-neighbour assessment baseline fallback, return an estimate when fallback-based estimation is allowed, and mark the response and UI with a non-blocking missing-baseline warning for transparency.
- **FR-01-018**: If some open-data features are unavailable because of missing datasets, timeouts, or routing unavailability, the system MUST proceed with a partial feature set only when supported, MUST return a warning describing the missing feature coverage, and the UI MUST NOT imply that missing features are zero-valued.
- **FR-01-019**: If the valuation engine fails, the system MUST log the failure with a correlation or request identifier, MUST indicate that the estimate could not be produced, MUST provide a retry path in the UI, and MUST NOT display an estimated value for the failed request.
- **FR-01-020**: The UI MUST apply estimate formatting consistently across views so the same estimate is not shown with conflicting currency or rounding formats.
- **FR-01-021**: For repeated requests with the same input while dataset versions, baseline data, and model version remain unchanged, the system MUST return a consistent single estimated value within the configured rounding rule and consistent location summary and baseline metadata.
- **FR-01-022**: For each successful estimate request, the system MUST support request tracing by either including a correlation or request identifier in the response or logging one that can be tied to the client session so the request can be traced for support and debugging.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-13-01 | FR-01-001, FR-01-002, FR-01-003, FR-01-004, FR-01-005, FR-01-006, FR-01-007, FR-01-008, FR-01-009, FR-01-010, FR-01-011, FR-01-012 |
| AT-13-02 | FR-01-001, FR-01-013 |
| AT-13-03 | FR-01-003, FR-01-014 |
| AT-13-04 | FR-01-015 |
| AT-13-05 | FR-01-015, FR-01-016 |
| AT-13-06 | FR-01-017 |
| AT-13-07 | FR-01-018 |
| AT-13-08 | FR-01-019 |
| AT-13-09 | FR-01-008, FR-01-020 |
| AT-13-10 | FR-01-021 |
| AT-13-11 | FR-01-022 |

#### Flow Steps or Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow Step 1 | FR-01-001 |
| Main Flow Step 2 | FR-01-002 |
| Main Flow Step 3 | FR-01-003, FR-01-014 |
| Main Flow Step 4 | FR-01-004, FR-01-015, FR-01-016 |
| Main Flow Step 5 | FR-01-005, FR-01-012, FR-01-017 |
| Main Flow Step 6 | FR-01-006, FR-01-018 |
| Main Flow Step 7 | FR-01-007, FR-01-019, FR-01-021 |
| Main Flow Step 8 | FR-01-008, FR-01-011, FR-01-020 |
| Main Flow Step 9 | FR-01-009, FR-01-022 |
| Main Flow Step 10 | FR-01-010, FR-01-013 |
| Alternate Flow 5a | FR-01-017 |
| Alternate Flow 6a | FR-01-018 |
| Exception Flow 3a | FR-01-014 |
| Exception Flow 4a | FR-01-015, FR-01-016 |
| Exception Flow 7a | FR-01-019 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of successful valid-request test runs, the system returns exactly one estimated value and the UI displays one prominent single-value result together with a timestamp and location summary.
- **SC-002**: In 100% of invalid, ambiguous, or unresolvable-input test runs, the system blocks estimation until the issue is corrected, provides an actionable correction or retry path, and shows no stale estimate for the failed request.
- **SC-003**: In 100% of missing-baseline or partial-feature test runs where fallback behavior is supported, the system still returns at most one estimate and surfaces explicit non-blocking warnings describing the fallback or missing coverage.
- **SC-004**: Under normal load, at least 95% of successful estimate requests for locations with cached or precomputed features complete within 3 seconds.
- **SC-005**: In 100% of repeated-request test runs with unchanged input, dataset versions, baseline data, and model version, the returned estimate remains consistent within the configured rounding rule and the accompanying metadata remains consistent.
