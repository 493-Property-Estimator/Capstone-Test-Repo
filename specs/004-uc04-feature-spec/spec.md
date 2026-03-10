# Feature Specification: Normalize Property Input to Canonical Location ID

**Feature Branch**: `004-uc04-feature-spec`  
**Created**: 2026-03-09  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-04.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-04-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-04-AT.md Hard rules: 1) Copy the use case flows directly into spec.md (main + alternate + exception flows). Preserve ordering and intent. Do not invent steps. 2) You may make style/grammar improvements only if meaning is unchanged. 3) Extract functional requirements (FRs) ONLY from: - the flows in UC-04.md, and - the checks/expectations in UC-04-AT.md Do not add “nice-to-have” requirements that aren’t supported by those sources. 4) Keep implementation constraints: Python, vanilla HTML/CSS/JS. 5) Treat this use case as its own feature branch (branch naming suggestion is fine, but don’t actually run git commands unless asked). Spec contents required: - Feature name (from use case title) - Summary / goal - Actors - Preconditions - Triggers - Main flow (verbatim from use case) - Alternate flows (verbatim) - Exception/error flows (verbatim) - Data involved (only what the use case mentions) - Functional requirements list (numbered FR-01-001, FR-01-015, …) - Traceability section mapping: - each acceptance test → related FRs - each flow step (or flow section) → related FRs (coarse mapping is fine) Output: - Update/produce the spec.md for this feature. If Spec-Kit expects a per-feature folder/file, follow the tool’s convention, but the content must match the above constraints."

## Use Case Overview

**Summary / Goal**: Ensure that any property input (address, latitude/longitude, or map click) is converted into a single canonical location identifier so that downstream valuation, caching, and feature computation processes operate consistently.

**Actors**:
- Primary Actor: Backend System
- Secondary Actors: Geocoding Service; Spatial Database; Boundary Validation Service

**Preconditions**:
- The Property Value Estimator system is operational.
- Required spatial datasets (parcels, grids, boundaries) are available.
- If the input is an address, the geocoding service is available.
- The input has passed initial format validation (e.g., valid address format or coordinate ranges).

**Trigger**: The system receives a property input (address, coordinates, or map click) that requires normalization before valuation.

**Main Flow (verbatim)**:
1. The system receives a property input (address, latitude/longitude, or map click coordinates).
2. If the input is an address, the system sends the address to the geocoding service.
3. The geocoding service returns geographic coordinates.
4. The system verifies that the coordinates fall within the supported geographic boundary.
5. The system queries the spatial database to determine the corresponding parcel, grid cell, or predefined spatial unit.
6. The system generates a canonical location ID based on the resolved spatial unit.
7. The system stores or forwards the canonical location ID to downstream valuation components.

**Alternate Flows (verbatim)**:
- **5a**: No parcel or spatial unit found for valid in-bound coordinates
  - 5a1: The system assigns the location to a fallback spatial unit (e.g., grid cell).
  - 5a2: The system generates a canonical location ID based on the fallback unit.
  - 5a3: The scenario resumes at Step 7.
- **6a**: Canonical ID generation conflict or duplication detected
  - 6a1: The system resolves the conflict using predefined rules (e.g., deterministic ID generation).
  - 6a2: The system ensures the canonical ID is stable and unique before proceeding.

**Exception / Error Flows (verbatim)**:
- **2a**: Geocoding service fails or returns no match
  - 2a1: The system logs the normalization failure.
  - 2a2: The system returns an error indicating normalization could not be completed.
  - 2a3: The use case ends in Failed End Condition.
- **4a**: Coordinates fall outside supported geographic boundary
  - 4a1: The system logs the boundary validation failure.
  - 4a2: The system returns an error indicating the location is unsupported.
  - 4a3: The use case ends in Failed End Condition.

**Data Involved (use case only)**:
- Property input
- Address
- Latitude/longitude
- Map click coordinates
- Geographic coordinates
- Supported geographic boundary
- Parcel
- Grid cell
- Predefined spatial unit
- Fallback spatial unit
- Canonical location ID
- Downstream valuation components

## Assumptions & Constraints

- Implementation constraints: Python, vanilla HTML/CSS/JS.
- The feature scope is limited to normalization of property input into a canonical location ID and the resulting pass/fail handoff to downstream valuation processing.

## Clarifications

### Session 2026-03-09

- Q: When coordinates match overlapping spatial units, which unit should normalization resolve? → A: Prefer the most specific containing unit: parcel first, then other predefined units, then grid cell.
- Q: What canonical ID structure should the system use? → A: Use a type-prefixed canonical ID based on the resolved unit, such as parcel-based IDs for parcels and grid-based IDs for fallback/grid units.
- Q: What fallback spatial unit should the system assign when no parcel or primary spatial unit is found? → A: Always use a grid cell as the fallback spatial unit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Normalize Valid Property Input (Priority: P1)

As the backend system, I need valid property input to normalize into a canonical location ID so downstream valuation components can proceed consistently.

**Why this priority**: This is the primary success path and the purpose of UC-04.

**Independent Test**: Submit a valid address or valid in-bound coordinates and verify the system returns or forwards a non-empty canonical location ID after spatial resolution.

**Acceptance Scenarios**:
1. **Given** a valid address with successful geocoding, in-bound coordinates, and a resolved spatial unit, **When** the system performs normalization, **Then** it generates and returns or forwards a canonical location ID. (AT-01)
2. **Given** valid in-bound coordinates and a resolved spatial unit, **When** the system performs normalization, **Then** it generates and returns or forwards a canonical location ID without geocoding. (AT-02)
3. **Given** the same valid input is normalized repeatedly with unchanged spatial data, **When** normalization runs multiple times, **Then** the canonical location ID remains identical. (AT-08)
4. **Given** equivalent address and coordinate representations of the same location, **When** each input is normalized, **Then** both normalization paths produce the same canonical location ID. (AT-09)

---

### User Story 2 - Stop Processing on Normalization Failure (Priority: P2)

As the backend system, I need normalization failures to stop downstream processing and return a specific error outcome so invalid or unsupported inputs do not continue into valuation.

**Why this priority**: Failure handling is required to protect downstream valuation consistency and to satisfy the failed end condition.

**Independent Test**: Force geocoding failure or out-of-bound coordinates and verify the system logs the failure, returns the expected error classification, and makes no downstream calls.

**Acceptance Scenarios**:
1. **Given** an address whose geocoding request fails or returns no match, **When** normalization is attempted, **Then** the system logs the failure, returns a geocoding-related normalization error, and produces no canonical location ID. (AT-03)
2. **Given** coordinates outside the supported boundary, **When** normalization is attempted, **Then** the system logs an unsupported-location error, produces no canonical location ID, and stops processing. (AT-04)
3. **Given** any normalization failure, **When** the normalization step ends in failure, **Then** downstream valuation, feature computation, and caching do not proceed. (AT-10)

---

### User Story 3 - Resolve Fallback and ID Conflicts Deterministically (Priority: P3)

As the backend system, I need deterministic fallback and conflict handling so normalization still produces a stable canonical location ID when normal spatial resolution or ID generation encounters exceptions.

**Why this priority**: These paths preserve successful normalization when a primary parcel match is unavailable or when a generated ID conflicts with existing constraints.

**Independent Test**: Simulate no parcel found and ID conflict cases, then verify fallback selection and conflict resolution produce stable canonical IDs.

**Acceptance Scenarios**:
1. **Given** valid in-bound coordinates with no containing parcel or primary spatial unit, **When** the system applies fallback spatial assignment, **Then** it generates and forwards a canonical location ID based on the fallback unit. (AT-05)
2. **Given** identical inputs with no parcel found on repeated runs, **When** the fallback rule is applied multiple times, **Then** the same fallback spatial unit and canonical location ID are produced each time. (AT-06)
3. **Given** canonical ID generation detects a duplication or conflict, **When** the system applies deterministic resolution rules, **Then** it produces a stable, unique canonical location ID. (AT-07)

### Edge Cases

- Geocoding service fails, times out, or returns no match for an address input.
- Coordinates from direct input or geocoding fall outside the supported geographic boundary.
- No parcel or primary spatial unit is found for valid in-bound coordinates.
- If no parcel or primary spatial unit is found, fallback assignment uses a grid cell rather than the nearest valid parcel.
- Canonical ID generation detects a duplication conflict or inconsistency with previously generated identifiers.
- Overlapping spatial units for the same coordinates must resolve to the most specific containing unit: parcel first, then other predefined units, then grid cell.
- Repeated normalization of identical inputs must produce the same canonical location ID when underlying spatial datasets have not changed.
- Equivalent address and coordinate inputs for the same location must converge to the same canonical location ID.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-01-001**: The system MUST receive a property input as an address, latitude/longitude, or map click coordinates for normalization. (Main Flow Step 1)
- **FR-01-015**: If the input is an address, the system MUST send the address to the geocoding service. (Main Flow Step 2)
- **FR-01-030**: For address input, the system MUST use the geographic coordinates returned by the geocoding service for subsequent normalization steps. (Main Flow Step 3, AT-01)
- **FR-01-045**: The system MUST verify that normalization coordinates fall within the supported geographic boundary. (Main Flow Step 4, AT-01, AT-02, AT-04)
- **FR-01-060**: The system MUST query the spatial database to determine the corresponding parcel, grid cell, or predefined spatial unit for valid in-bound coordinates. (Main Flow Step 5, AT-01, AT-02)
- **FR-01-068**: If multiple spatial units overlap at the same coordinates, the system MUST resolve the most specific containing unit in this order: parcel, then other predefined spatial units, then grid cell. (UC-04 Related Information: Open Issues)
- **FR-01-075**: The system MUST generate a canonical location ID based on the resolved spatial unit. (Main Flow Step 6, AT-01, AT-02)
- **FR-01-083**: The canonical location ID MUST be type-prefixed by the resolved unit so parcel resolutions produce parcel-based IDs and grid or fallback resolutions produce grid-based or fallback-unit IDs. (UC-04 Related Information: Open Issues, AT-01, AT-05)
- **FR-01-090**: The system MUST store or forward the canonical location ID to downstream valuation components after successful normalization. (Main Flow Step 7, AT-01, AT-02)
- **FR-01-105**: If geocoding fails or returns no match, the system MUST log the normalization failure, return an error indicating normalization could not be completed, and end normalization without producing a canonical location ID. (Exception Flow 2a, AT-03)
- **FR-01-120**: If geocoding fails or returns no match, the system MUST NOT perform spatial database lookup after the geocoding failure. (AT-03)
- **FR-01-135**: If coordinates fall outside the supported geographic boundary, the system MUST log the boundary validation failure, return an error indicating the location is unsupported, and end normalization without producing a canonical location ID. (Exception Flow 4a, AT-04)
- **FR-01-150**: If coordinates are outside the supported geographic boundary, the system MUST NOT perform spatial-unit lookup or downstream processing. (AT-04, AT-10)
- **FR-01-165**: If no parcel or spatial unit is found for valid in-bound coordinates, the system MUST assign the location to a grid-cell fallback spatial unit and generate a canonical location ID based on that fallback unit. (Alternate Flow 5a, AT-05)
- **FR-01-180**: Fallback spatial-unit assignment MUST be deterministic so identical inputs under identical conditions produce the same fallback unit and canonical location ID. (AT-06)
- **FR-01-195**: If canonical ID generation detects a conflict or duplication, the system MUST resolve the conflict using predefined deterministic rules before proceeding. (Alternate Flow 6a, AT-07)
- **FR-01-210**: The system MUST ensure the canonical location ID is stable and unique before forwarding it downstream. (Alternate Flow 6a, AT-07, AT-08)
- **FR-01-225**: Repeated normalization of identical inputs MUST produce the same canonical location ID when the underlying spatial datasets have not changed. (AT-08)
- **FR-01-240**: Equivalent address and coordinate inputs for the same location MUST produce the same canonical location ID, or a documented equivalent result. (AT-09)
- **FR-01-255**: When normalization fails, the system MUST NOT invoke downstream valuation, feature computation, or caching for that failed request. (Failed End Condition, AT-10)

### Non-Functional Requirements

- **NFR-01-001**: Normalization outcomes MUST be deterministic for identical inputs when the underlying spatial datasets have not changed. (AT-06, AT-08)
- **NFR-01-002**: Error outcomes MUST be specific enough to distinguish geocoding failure/no match from unsupported out-of-bound locations. (AT-03, AT-04)
- **NFR-01-003**: Implementation is constrained to Python with vanilla HTML/CSS/JS interfaces where user-facing interaction is required.

### Key Entities

- **Property Input**: The address, latitude/longitude, or map click coordinates submitted for normalization.
- **Geographic Coordinates**: The latitude/longitude pair used for boundary validation and spatial resolution.
- **Spatial Unit**: The parcel, grid cell, predefined spatial unit, or grid-cell fallback spatial unit associated with the coordinates.
- **Spatial Resolution Priority**: The deterministic precedence rule used when multiple spatial units contain the same coordinates: parcel first, then other predefined spatial units, then grid cell.
- **Canonical Location ID**: The stable identifier generated from the resolved spatial unit, type-prefixed by resolved unit type, and used by downstream valuation components.

### Traceability

**Acceptance Tests → Functional Requirements**:
- **AT-01** → FR-01-015, FR-01-030, FR-01-045, FR-01-060, FR-01-068, FR-01-075, FR-01-083, FR-01-090
- **AT-02** → FR-01-045, FR-01-060, FR-01-068, FR-01-075, FR-01-083, FR-01-090
- **AT-03** → FR-01-105, FR-01-120
- **AT-04** → FR-01-045, FR-01-135, FR-01-150
- **AT-05** → FR-01-083, FR-01-165
- **AT-06** → FR-01-180
- **AT-07** → FR-01-195, FR-01-210
- **AT-08** → FR-01-210, FR-01-225
- **AT-09** → FR-01-240
- **AT-10** → FR-01-150, FR-01-255

**Flow Steps / Sections → Functional Requirements (coarse)**:
- **Main Flow Step 1** → FR-01-001
- **Main Flow Steps 2-3** → FR-01-015, FR-01-030
- **Main Flow Step 4** → FR-01-045
- **Main Flow Step 5** → FR-01-060, FR-01-068
- **Main Flow Steps 6-7** → FR-01-075, FR-01-083, FR-01-090
- **Exception Flow 2a** → FR-01-105, FR-01-120
- **Exception Flow 4a** → FR-01-135, FR-01-150
- **Alternate Flow 5a** → FR-01-165, FR-01-180
- **Alternate Flow 6a** → FR-01-195, FR-01-210
- **Failed End Condition** → FR-01-255

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-01-001**: 100% of valid address normalization requests with successful geocoding, in-bound coordinates, and a resolved spatial unit produce a non-empty canonical location ID. (AT-01)
- **SC-01-002**: 100% of valid in-bound coordinate normalization requests produce a non-empty canonical location ID without geocoding. (AT-02)
- **SC-01-003**: 100% of geocoding failures or no-match outcomes return a geocoding-specific normalization failure and produce no canonical location ID. (AT-03)
- **SC-01-004**: 100% of out-of-bound normalization requests return an unsupported-location error, perform no spatial lookup, and produce no canonical location ID. (AT-04)
- **SC-01-005**: 100% of successful fallback normalizations produce a non-empty canonical location ID instead of failing when no parcel or primary spatial unit is found. (AT-05)
- **SC-01-006**: 100% of repeated identical normalization requests under unchanged spatial data return the same canonical location ID. (AT-06, AT-08)
- **SC-01-007**: 100% of detected canonical ID conflicts resolve to a stable, unique canonical location ID before downstream forwarding. (AT-07)
- **SC-01-008**: 100% of equivalent address and coordinate inputs for the same location return the same canonical location ID, or a documented equivalent result. (AT-09)
- **SC-01-009**: 100% of normalization failures prevent downstream valuation, feature computation, and caching calls for the failed request. (AT-10)
