# Feature Specification: Search by Address in the Map UI

**Feature Branch**: `024-address-map-search`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description derived from `Use Cases/UC-24.md`, `Scenarios/UC-24-Scenarios.md`, and `Acceptance Tests/UC-24-AT.md`

## Summary / Goal

Allow a general user to enter an address in the map interface so the map can navigate to the resolved property location and show valuation context for that property.

## Clarifications

### Session 2026-03-10

- Q: What should the map do when a resolved address is outside supported coverage? → A: Show the warning and keep the current map view unchanged.

## Actors

- **Primary Actor**: General User
- **Secondary Actors**: Geocoding/Location Resolver Service, Map Rendering Engine, Suggestion/Autocomplete Service

## Preconditions

- User has opened the map UI successfully.
- Map tiles and UI controls are loaded.
- Geocoding/Location Resolver service is reachable.
- User has an internet connection.

## Triggers

- User types an address into the search bar and submits the search (Enter key or search icon).

## Assumptions

- The map UI is already available as the entry point for search.
- The feature supports only the geographic coverage area defined by the product.
- Scenario narratives are supporting detail only; use case and acceptance tests remain the source of truth.

## Dependencies

- Availability of the map UI and map rendering engine
- Availability of the suggestion/autocomplete service for partial-address lookup
- Availability of the geocoding/location resolver service for full-address resolution

## Implementation Constraints

- Backend and service-side implementation must remain in Python.
- Frontend implementation must remain in vanilla HTML, CSS, and JavaScript.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navigate to a searched address (Priority: P1)

As a general user, I want to search for a valid address from the map UI so the map moves to that property and shows the location I searched for.

**Why this priority**: This is the core UC-24 outcome and the primary reason the search bar exists.

**Independent Test**: Can be fully tested by opening the map UI, entering a valid address, selecting a suggestion or submitting the full address, and confirming the map navigates to the resolved location with location labeling.

**Acceptance Scenarios**:

1. **Given** the map UI is loaded, **When** the user views the landing page, **Then** the search bar is visible, enabled, and shows helper text. (`AT-UC24-001`)
2. **Given** autocomplete is available, **When** the user types a valid partial address, **Then** ranked suggestions appear for selection. (`AT-UC24-002`)
3. **Given** a valid suggestion is available, **When** the user selects it, **Then** the map pans and zooms to the property and displays a marker or highlight. (`AT-UC24-003`)
4. **Given** the user enters a full valid address, **When** the user submits it without clicking a suggestion, **Then** the map resolves and navigates to that location without showing an error. (`AT-UC24-004`)

---

### User Story 2 - Get useful guidance when search input is unclear or unsupported (Priority: P1)

As a general user, I want the system to explain ambiguous, invalid, missing, or unsupported search results so I can correct the query instead of being silently misdirected.

**Why this priority**: UC-24 explicitly includes ambiguity, no-result, invalid-input, and coverage handling as required user-visible behavior.

**Independent Test**: Can be fully tested by submitting ambiguous, invalid, unmatched, and out-of-coverage addresses and verifying the UI provides explicit guidance and controlled map behavior.

**Acceptance Scenarios**:

1. **Given** the submitted address is ambiguous, **When** search resolution returns multiple candidates, **Then** the system presents candidate choices and waits for the user to choose one. (`AT-UC24-005`)
2. **Given** the submitted address has no match, **When** the search completes, **Then** the system displays a clear no-results message and leaves the map unchanged. (`AT-UC24-006`)
3. **Given** the input is too short or invalid, **When** the user submits it, **Then** the system prompts for more detail and avoids excessive request traffic. (`AT-UC24-007`)
4. **Given** the resolved address is outside supported coverage, **When** the search completes, **Then** the system shows a coverage warning and applies the defined out-of-coverage map behavior. (`AT-UC24-008`)

---

### User Story 3 - Recover cleanly from dependency failures (Priority: P2)

As a general user, I want the search UI to fail gracefully when geocoding is unavailable so I am not left with a broken or endlessly loading search interaction.

**Why this priority**: Dependency failure handling is necessary for predictable user behavior and is explicitly called out in both UC-24 and its acceptance tests.

**Independent Test**: Can be fully tested by simulating a geocoding outage, submitting a valid address, and confirming the UI shows an actionable failure message without changing the map state.

**Acceptance Scenarios**:

1. **Given** the geocoding service is unavailable, **When** the user submits a valid address, **Then** the UI reports search unavailability, avoids an infinite loading state, and supports retry after the service returns. (`AT-UC24-009`)

### Edge Cases

- The user enters only one or two characters.
- Autocomplete returns no suggestions for the partial address.
- The submitted address resolves to multiple candidates.
- The submitted address resolves outside supported coverage.
- The geocoding service is unavailable after the user submits a search.
- The submitted address cannot be resolved at all.

## Requirements *(mandatory)*

### Main Flow (verbatim from use case)

1. **User** opens the map UI.
2. **System** displays a map view with a visible address search bar.
3. **User** begins typing an address (street, city, postal code).
4. **System** sends partial input to the Autocomplete service.
5. **Autocomplete service** returns suggested addresses ranked by relevance.
6. **System** displays suggestions in a dropdown list.
7. **User** selects a suggestion or completes typing and submits the search.
8. **System** sends the full address query to the Geocoding/Location Resolver service.
9. **Geocoding service** resolves the address into a coordinate (lat/long) and canonical address format.
10. **System** pans and zooms the map to the returned coordinate.
11. **System** places a marker or highlight at the resolved property location.
12. **System** displays the canonical address label and optional context (region, neighborhood).
13. **User** can now request an estimate or adjust map filters/layers.

### Alternate Flows (verbatim from use case)

- **3a**: User enters incomplete input (too short)
  - **3a1**: System displays "Enter more details" and does not call geocoding service.
- **5a**: Autocomplete returns no suggestions
  - **5a1**: System displays "No suggestions found" but still allows user to submit full query.
- **7a**: User submits a misspelled or ambiguous address
  - **7a1**: Geocoding returns multiple candidate results.
  - **7a2**: System displays candidate list (did you mean?) with map previews.
  - **7a3**: User selects the correct address and system continues at step 10.

### Exception / Error Flows (verbatim from use case)

- **8a**: Geocoding service is unavailable
  - **8a1**: System displays "Search unavailable right now" and logs error for monitoring.
- **9a**: Address not found
  - **9a1**: System displays "No matching address found" and keeps map unchanged.
  - **9a2**: System suggests alternative input formats (postal code, city, coordinates).
- **10a**: User searches an address outside supported coverage area
  - **10a1**: System displays "Region not supported" warning.
  - **10a2**: Map optionally pans to nearest supported boundary region.

### Data Involved

- User-entered address text
- Partial address input sent for autocomplete
- Suggested addresses ranked by relevance
- Full address query submitted for resolution
- Resolved coordinate (latitude/longitude)
- Canonical address format
- Canonical address label
- Optional context such as region or neighborhood
- Candidate address results for ambiguous searches
- Coverage status for the resolved location

### Functional Requirements

- **FR-01-001**: The system MUST display a visible, enabled address search bar when the map UI loads.
- **FR-01-002**: The search bar MUST provide placeholder or helper text indicating the expected address input.
- **FR-01-003**: The system MUST allow the user to type an address in the search bar, including street, city, and postal code information.
- **FR-01-004**: The system MUST debounce partial address input before requesting autocomplete results.
- **FR-01-005**: When partial input is sufficient, the system MUST send that input to the autocomplete service and display returned suggestions ranked by relevance in a dropdown list.
- **FR-01-006**: Autocomplete suggestions MUST show the full address with city information, and the UI MUST indicate match confidence or type when that information is available.
- **FR-01-007**: If suggestion retrieval is delayed, the UI MUST provide a visible loading indication while suggestions are pending.
- **FR-01-008**: When the user enters incomplete input that is too short, the system MUST display "Enter more details" and MUST NOT call the geocoding service.
- **FR-01-009**: When autocomplete returns no suggestions, the system MUST display "No suggestions found" and still allow the user to submit the full query.
- **FR-01-010**: The user MUST be able to select an autocomplete suggestion or submit a full address search using Enter or the search control.
- **FR-01-011**: When a full address is submitted and can be resolved, the system MUST send the full address query to the geocoding/location resolver service and obtain the resolved coordinate and canonical address format.
- **FR-01-012**: After a successful address resolution, the system MUST pan and zoom the map to the returned coordinate and place a marker or highlight at the resolved property location.
- **FR-01-013**: After successful resolution, the system MUST display the canonical address label and any supported location context, such as region or neighborhood.
- **FR-01-014**: When the submitted address is ambiguous, the system MUST present multiple candidate results, MUST NOT silently auto-select one candidate, and MUST allow the user to select a candidate before continuing navigation.
- **FR-01-015**: When the submitted address cannot be found, the system MUST display a clear no-results message, keep the map unchanged, and suggest alternative input formats.
- **FR-01-016**: When the resolved address is outside the supported coverage area, the system MUST display a "Region not supported" warning and keep the current map view unchanged.
- **FR-01-017**: When the geocoding service is unavailable, the system MUST display a "Search unavailable" message, MUST NOT remain in an infinite loading state, MUST allow the user to retry after service restoration, and MUST log the failure for monitoring.
- **FR-01-018**: When a full valid address is successfully resolved and displayed, the system MUST NOT display an error message for that search.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-UC24-001 | FR-01-001, FR-01-002 |
| AT-UC24-002 | FR-01-004, FR-01-005, FR-01-006, FR-01-007 |
| AT-UC24-003 | FR-01-010, FR-01-011, FR-01-012, FR-01-013 |
| AT-UC24-004 | FR-01-010, FR-01-011, FR-01-012, FR-01-018 |
| AT-UC24-005 | FR-01-014 |
| AT-UC24-006 | FR-01-015 |
| AT-UC24-007 | FR-01-004, FR-01-008 |
| AT-UC24-008 | FR-01-016 |
| AT-UC24-009 | FR-01-017 |

#### Flow Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow 1-3 | FR-01-001, FR-01-002, FR-01-003 |
| Main Flow 4-6 | FR-01-004, FR-01-005, FR-01-006, FR-01-007 |
| Main Flow 7-9 | FR-01-010, FR-01-011 |
| Main Flow 10-13 | FR-01-012, FR-01-013 |
| Alternate Flow 3a | FR-01-008 |
| Alternate Flow 5a | FR-01-009 |
| Alternate Flow 7a | FR-01-014, FR-01-012, FR-01-013 |
| Exception Flow 8a | FR-01-017 |
| Exception Flow 9a | FR-01-015 |
| Exception Flow 10a | FR-01-016 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of map UI landing-page loads show an enabled address search bar with helper text before the user begins a search.
- **SC-002**: In acceptance testing, 100% of valid supported-address searches completed by suggestion selection or full-query submission navigate the map to the resolved location and show a marker or highlight.
- **SC-003**: In acceptance testing, 100% of ambiguous, no-result, invalid-input, and out-of-coverage searches produce explicit user guidance instead of silent navigation.
- **SC-004**: In acceptance testing, 100% of simulated geocoding outages produce a recoverable search-unavailable message without leaving the search UI in an endless loading state.
