# Feature Specification: Show Missing-Data Warnings in UI

**Feature Branch**: `026-missing-data-warnings`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-26.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-26-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-26-AT.md Hard rules: 1) Copy the use case flows directly into spec.md (main + alternate + exception flows). Preserve ordering and intent. Do not invent steps. 2) You may make style/grammar improvements only if meaning is unchanged. 3) Extract functional requirements (FRs) ONLY from: - the flows in UC-26.md, and - the checks/expectations in UC-26-AT.md Do not add nice-to-have requirements that are not supported by those sources. 4) Keep implementation constraints: Python, vanilla HTML/CSS/JS. 5) Treat this use case as its own feature branch (branch naming suggestion is fine, but do not actually run git commands unless asked). Spec contents required: - Feature name (from use case title) - Summary / goal - Actors - Preconditions - Triggers - Main flow (verbatim from use case) - Alternate flows (verbatim) - Exception/error flows (verbatim) - Data involved (only what the use case mentions) - Functional requirements list (numbered FR-01-001, FR-01-015, ...) - Traceability section mapping: - each acceptance test to related FRs - each flow step (or flow section) to related FRs (coarse mapping is fine) Output: - Update/produce the spec.md for this feature. If Spec-Kit expects a per-feature folder/file, follow the tool’s convention, but the content must match the above constraints."

## Summary

A user is informed when an estimate was generated with missing or approximated factors so they do not over-trust the estimate and can interpret confidence correctly. The feature must clearly communicate missing or approximated data, present a confidence/completeness summary, and keep the estimate usable.

## Clarifications

### Session 2026-03-10

- Q: For standard partial-data results, should the UI use a panel, a banner, or both? → A: Standard partial-data warnings use a warning panel with a banner-style header/message.
- Q: Should the confidence indicator show a qualitative label, a percentage, or both? → A: Show both a percentage and a qualitative label when available.

## Actors

- Primary actor: General User
- Secondary actors: Estimate API, Valuation Engine

## Preconditions

- Estimate API response includes metadata describing missing factors and completeness.
- UI has a component to render warnings and confidence indicators.

## Triggers

- User requests an estimate and receives a response that includes missing-data flags or reduced confidence.

## Implementation Constraints

- The feature must fit the existing project constraints of Python and vanilla HTML/CSS/JS.

## User Scenarios & Testing

### User Story 1 - Review estimate confidence and warnings (Priority: P1)

As a user requesting a property estimate, I need the UI to show confidence, completeness, and missing-data warnings so I can judge how much to trust the estimate.

**Why this priority**: This is the core user value defined by UC-26 and is the primary protection against over-trusting degraded estimates.

**Independent Test**: Can be fully tested by requesting estimates for full-coverage and partial-coverage properties and verifying the confidence display, warning behavior, completeness summary, and factor breakdown.

**Acceptance Scenarios**:

1. **Given** a full-coverage property, **When** the user requests an estimate, **Then** the UI shows high confidence, no missing-data warnings, and a full breakdown.
2. **Given** an estimate with a missing optional dataset, **When** the user observes the result, **Then** the UI shows a specific warning, reduced confidence, a completeness summary, a factor breakdown with the unavailable factor marked, and a tooltip explaining the impact.
3. **Given** warning details are available, **When** the user expands the warning panel, **Then** the UI shows the missing or approximated factors and explains their impact without breaking the layout.

---

### User Story 2 - Understand degraded and fallback estimates (Priority: P2)

As a user receiving an estimate with major gaps or approximations, I need the UI to clearly distinguish severe warning cases from minor ones so I can interpret the result appropriately without being blocked from viewing it.

**Why this priority**: UC-26 extensions require distinct handling for very low confidence, fallback computation, and minor missing factors.

**Independent Test**: Can be tested by simulating very low confidence, routing fallback, and minor missing-factor responses and verifying the severity-specific UI messaging.

**Acceptance Scenarios**:

1. **Given** an estimate with very low confidence, **When** the user views the result, **Then** a prominent warning appears, details are expandable, and the estimate remains visible.
2. **Given** a routing fallback response, **When** the user views the result, **Then** the UI states that straight-line distance was used and adjusts confidence to reflect the approximation.
3. **Given** only a minor factor is missing, **When** the user views the result, **Then** the UI shows a small non-blocking notice instead of a prominent warning panel.

---

### User Story 3 - Continue after dismiss or malformed metadata (Priority: P3)

As a user, I need warning interactions and degraded metadata handling to remain usable so I can keep using the estimate even when I dismiss warnings or the response metadata is incomplete.

**Why this priority**: The use case explicitly requires non-blocking behavior and graceful handling of incomplete metadata.

**Independent Test**: Can be tested by collapsing the warning panel and by simulating malformed metadata, then verifying the persistent indicator, restore behavior, generic warning, and absence of crashes.

**Acceptance Scenarios**:

1. **Given** a warning panel is visible, **When** the user dismisses it, **Then** the panel collapses, a persistent indicator remains visible, and the panel can be reopened from that indicator.
2. **Given** the estimate response metadata is incomplete, **When** the UI processes the response, **Then** the estimate remains visible, a generic warning is shown, and the issue is logged for debugging.

### Edge Cases

- Full coverage returns high confidence and no warnings.
- Many factors are missing and confidence is very low.
- Only a minor factor is missing and confidence remains high.
- Routing data is unavailable and straight-line approximation is used.
- Coverage gaps make data unavailable for a region.
- Warning metadata is incomplete or malformed.

## Main Flow

## Main Success Scenario

1. **User** selects a property on the map.
2. **User** requests an estimate (button click or auto-estimate trigger).
3. **System** calls the Estimate API with the property reference.
4. **Estimate API** returns an estimate response containing:
   - baseline assessment value,
   - final estimated price,
   - factor breakdown,
   - completeness/confidence score,
   - missing-data indicators (e.g., missing crime, missing routing).
5. **UI** parses the response and identifies missing or approximated factors.
6. **UI** displays a confidence indicator (e.g., high/medium/low).
7. **UI** displays a warning panel listing missing factors (e.g., "Crime data unavailable in this region").
8. **UI** allows the user to expand details showing how missing factors affected the estimate.
9. **User** reviews warnings and continues exploring or adjusting filters.

## Alternate Flows

## Extensions

- **4a**: Many factors are missing (very low confidence)
  - **4a1**: UI shows a high-severity warning banner.
  - **4a2**: UI recommends user widen search radius or select another nearby area for comparison.
- **4b**: Only minor factors missing (small confidence reduction)
  - **4b1**: UI shows a small non-blocking notice (tooltip or icon).
- **7a**: Missing factor is due to fallback computation (routing -> straight-line)
  - **7a1**: UI displays "Routing unavailable; used straight-line approximation."
  - **7a2**: UI tags the estimate as "Approximate distances used."
- **7b**: Missing factor is due to dataset coverage gaps
  - **7b1**: UI displays message explaining "Data not available for rural region."
- **8a**: User dismisses warnings
  - **8a1**: UI collapses warning panel but keeps a small warning icon visible.
  - **8a2**: User can reopen warnings later.

## Exception/Error Flows

- **5a**: Estimate API returns incomplete metadata
  - **5a1**: UI displays generic warning: "Some data may be missing."
  - **5a2**: System logs the malformed response for debugging.

## Data Involved

- Property reference
- Baseline assessment value
- Final estimated price
- Factor breakdown
- Completeness/confidence score
- Missing-data indicators

## Requirements

### Functional Requirements

- **FR-01-001**: The system MUST allow the user to request an estimate for a selected property.
- **FR-01-002**: The system MUST call the Estimate API with the property reference when an estimate is requested.
- **FR-01-003**: The system MUST process estimate responses that include baseline assessment value, final estimated price, factor breakdown, completeness/confidence score, and missing-data indicators.
- **FR-01-004**: The UI MUST identify missing or approximated factors from the estimate response metadata.
- **FR-01-005**: The UI MUST display a confidence indicator for the estimate result.
- **FR-01-005**: The UI MUST display a confidence indicator for the estimate result and, when available from the estimate response, show both a percentage value and a qualitative label.
- **FR-01-006**: The UI MUST display no missing-data warning when the estimate response indicates full coverage and no missing factors.
- **FR-01-007**: The UI MUST display a warning panel listing missing factors when missing-data indicators are present.
- **FR-01-007**: The UI MUST display a warning panel listing missing factors when missing-data indicators are present, and the panel MUST present its primary warning message in a banner-style header for standard partial-data cases.
- **FR-01-008**: The UI MUST show a completeness summary when confidence or completeness metadata indicates partial data.
- **FR-01-009**: The UI MUST display a factor breakdown that distinguishes unavailable factors from available factors.
- **FR-01-010**: The UI MUST allow the user to expand warning details to see how missing or approximated factors affected the estimate.
- **FR-01-011**: The UI MUST display a prominent high-severity warning for very low-confidence estimates while still allowing the user to view the estimate.
- **FR-01-012**: The UI MUST recommend widening the search radius or selecting another nearby area when many factors are missing and confidence is very low.
- **FR-01-013**: The UI MUST show a small non-blocking notice when only minor factors are missing.
- **FR-01-014**: The UI MUST display a specific routing fallback message when straight-line approximation is used because routing is unavailable.
- **FR-01-015**: The UI MUST identify estimates that use approximate distances.
- **FR-01-016**: The UI MUST display a message when data is unavailable because of regional dataset coverage gaps.
- **FR-01-017**: The UI MUST allow the user to dismiss or collapse warnings without blocking continued use of the estimate.
- **FR-01-018**: The UI MUST keep a visible warning indicator after dismissal and allow the user to reopen warnings later.
- **FR-01-019**: The UI MUST handle incomplete estimate metadata without crashing.
- **FR-01-020**: The UI MUST display a generic warning when estimate metadata is incomplete.
- **FR-01-021**: The system MUST log malformed estimate metadata for debugging.
- **FR-01-022**: The confidence display MUST reflect reductions caused by missing data or fallback approximations.
- **FR-01-023**: The warning details presentation MUST keep the layout usable while details are expanded.

### Non-Functional Requirements

- **NFR-001**: Warning and confidence information MUST be understandable enough for users to interpret estimate reliability correctly.
- **NFR-002**: Warning behavior MUST remain non-blocking so users can continue exploring or adjusting filters after viewing an estimate.
- **NFR-003**: The feature implementation MUST remain within the project constraints of Python and vanilla HTML/CSS/JS.

### Key Entities

- **Estimate Response**: The estimate result returned by the Estimate API, including baseline assessment value, final estimated price, factor breakdown, completeness/confidence score, and missing-data indicators.
- **Missing-Data Indicator**: Metadata describing missing or approximated factors affecting the estimate.
- **Warning State**: The UI state that determines whether warnings are expanded, collapsed, or represented by a persistent indicator.

## Traceability

### Acceptance Test to Functional Requirement Mapping

- **AT-UC26-001** -> FR-01-001, FR-01-003, FR-01-005, FR-01-006, FR-01-009
- **AT-UC26-002** -> FR-01-001, FR-01-004, FR-01-005, FR-01-007, FR-01-008, FR-01-009, FR-01-022
- **AT-UC26-003** -> FR-01-001, FR-01-014, FR-01-015, FR-01-022
- **AT-UC26-004** -> FR-01-001, FR-01-010, FR-01-011, FR-01-012
- **AT-UC26-005** -> FR-01-010, FR-01-023
- **AT-UC26-006** -> FR-01-017, FR-01-018
- **AT-UC26-007** -> FR-01-019, FR-01-020, FR-01-021

### Flow Section to Functional Requirement Mapping

- **Main Success Scenario 1-3** -> FR-01-001, FR-01-002
- **Main Success Scenario 4-5** -> FR-01-003, FR-01-004
- **Main Success Scenario 6-8** -> FR-01-005, FR-01-007, FR-01-008, FR-01-009, FR-01-010
- **Main Success Scenario 9** -> FR-01-017
- **Extension 4a** -> FR-01-011, FR-01-012
- **Extension 4b** -> FR-01-013
- **Extension 7a** -> FR-01-014, FR-01-015, FR-01-022
- **Extension 7b** -> FR-01-016
- **Extension 8a** -> FR-01-017, FR-01-018
- **Exception 5a** -> FR-01-019, FR-01-020, FR-01-021

## Assumptions

- Acceptance-test examples that mention specific confidence percentages, completeness summaries, and factor labels are treated as valid examples of required UI behavior for this feature.
- The scenario narrative was reviewed for context only and was not used to create additional functional requirements beyond the use case and acceptance tests.

## Dependencies

- Estimate API responses must continue providing the metadata fields referenced by UC-26 and its acceptance tests.
- The estimate UI must provide warning and confidence display areas that this feature can use.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In 100% of full-coverage estimate test runs, users see a confidence indicator, no missing-data warning, and a full factor breakdown.
- **SC-002**: In 100% of partial-data, fallback, and low-confidence test runs, users see a warning state that identifies the missing or approximated factors and shows the adjusted confidence or completeness information.
- **SC-003**: In 100% of dismiss-and-restore test runs, users can collapse warnings, retain a persistent indicator, reopen the warning details, and continue viewing the estimate throughout.
- **SC-004**: In 100% of malformed-metadata test runs, the UI keeps the estimate visible, shows a generic warning, and records the issue for debugging without a crash.
