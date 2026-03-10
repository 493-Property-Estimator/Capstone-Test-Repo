# Feature Specification: Show Top Contributing Factors

**Feature Branch**: `[015-top-contributing-factors]`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description referencing `Use Cases/UC-15.md`, `Scenarios/UC-15-Scenarios.md`, and `Acceptance Tests/UC-15-AT.md`

## Overview

### Feature Name

Show Top Contributing Factors

### Summary / Goal

Enable the user to understand why an estimate differs from the baseline by viewing the most influential positive and negative contributing factors with readable labels and supporting values.

### Actors

- **Primary Actor**: General User
- **Secondary Actors**: Explainability/Attribution Service; Valuation Engine; Feature Store/Database; Map UI (layer visualization)

### Preconditions

- A point estimate has been computed for the requested location.
- The system has computed and retained the feature values used for valuation for this request, or can recompute them consistently.
- The system has a defined method to derive contributions, such as linear adjustments, feature importance attribution, or SHAP-like values.

### Trigger

The user requests the estimate details or explanation view, such as by expanding "Why this value?"

### Assumptions

- `Use Cases/UC-15.md` is the source of truth for flows, actors, preconditions, and trigger.
- `Acceptance Tests/UC-15-AT.md` is the source of truth for verifiable behavior and output checks.
- `Scenarios/UC-15-Scenarios.md` was used only to sharpen summary wording and user-story framing; no functional behavior was derived from it beyond the use case and acceptance tests.
- Contribution magnitudes may be shown as dollar impacts or normalized scores as long as the chosen format is consistent and clearly labeled.

### Implementation Constraints

- This feature must remain within the project's Python and vanilla HTML/CSS/JS constraints.

## Clarifications

### Session 2026-03-10

- Q: How should contribution magnitudes be presented? → A: Allow either dollar impacts or normalized scores by configuration, but require the configured format to be consistent and clearly labeled.
- Q: How many top factors should the UI show by default? → A: Keep the top-N count configurable and enforce the configured default in the UI.
- Q: Which factors should support map highlighting? → A: Only factors with real map context should offer map highlighting; non-visualizable factors should show a clear unavailable state.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explain Why the Estimate Changed (Priority: P1)

As a general user, I want to open an explanation view and see the top factors that increased or decreased the estimate so I can understand why the estimate differs from the baseline.

**Why this priority**: This is the primary user-facing value of the feature and the core explanation path.

**Independent Test**: Can be fully tested by requesting an estimate with explanation support and verifying that the UI shows a ranked top-N list of positive and negative factors with readable labels, supporting values, and impact direction.

**Acceptance Scenarios**:

1. **Given** an estimate with baseline metadata, **When** the user opens "Why this value?", **Then** the UI displays a ranked list of contributing factors separated into increases and decreases, with human-readable labels, supporting values, impact direction, and top-N limits. (`AT-15-01`)
2. **Given** an explanation with baseline and point estimate available, **When** the user reviews the factors, **Then** signs are not contradictory and any numeric magnitudes are clearly labeled with consistent units or formatting. (`AT-15-02`)
3. **Given** factor items are displayed, **When** the UI renders them, **Then** units, rounding, and labels remain readable and consistent, with jargon avoided or explained. (`AT-15-03`)

---

### User Story 2 - Handle Partial or Unsupported Explanations Safely (Priority: P2)

As a general user, I want the estimate to remain usable even when explanation data is partial, unsupported, or unavailable so I can still rely on the main estimate flow.

**Why this priority**: Graceful handling of missing or unsupported explanation data prevents the explanation feature from degrading the core estimate experience.

**Independent Test**: Can be tested by forcing partial-feature, unsupported-attribution, and explainability-service failure conditions and verifying that the estimate remains visible while the UI shows the correct explanation fallback state.

**Acceptance Scenarios**:

1. **Given** some feature categories are unavailable, **When** the user opens "Why this value?", **Then** the UI shows available explanations, flags missing categories, avoids implying zero impact, and keeps the estimate visible. (`AT-15-04`)
2. **Given** numeric attribution is unsupported, **When** the user opens "Why this value?", **Then** the UI shows a qualitative explanation, labels it as qualitative, and notes the limitation. (`AT-15-05`)
3. **Given** the explainability service fails or times out, **When** the user opens "Why this value?", **Then** the UI shows an explanation-unavailable message, leaves the estimate visible and unchanged, and offers retry if supported without blocking other estimate interactions. (`AT-15-06`)

---

### User Story 3 - Support Map Context and Policy-Safe Presentation (Priority: P3)

As a general user, I want factor selections and factor presentation to remain accurate, policy-safe, and non-breaking so I can explore explanation context without confusion.

**Why this priority**: Map interactions, policy filtering, and repeatability matter after the base explanation flow and graceful degradation behavior are in place.

**Independent Test**: Can be tested by selecting visualizable and non-visualizable factors, applying policy filtering rules, and repeating the same request under fixed versions.

**Acceptance Scenarios**:

1. **Given** a factor corresponds to a map layer, **When** the user selects that factor, **Then** the UI highlights matching map context and can dismiss the highlight without losing the explanation panel. (`AT-15-07`)
2. **Given** a factor has no map visualization, **When** the user attempts to view it on the map, **Then** the UI shows factor details, avoids invalid layer display, and reports that map view is unavailable for that factor. (`AT-15-08`)
3. **Given** policy-based filtering or renaming applies, **When** the user opens "Why this value?", **Then** prohibited or misleading factor labels are omitted or renamed, and the UI shows a completeness note if coverage is materially reduced. (`AT-15-09`)
4. **Given** repeated requests with unchanged data and configuration, **When** the user opens "Why this value?" for each run, **Then** the top factors, ordering, supporting values, and units remain consistent within defined rounding and tie-breaking behavior. (`AT-15-10`)

### Edge Cases

- Feature values used for valuation are missing or only partially available.
- Numeric attribution is not supported for the current model or request type.
- The explainability service fails or times out after the estimate is available.
- A factor is too technical to present directly and needs a glossary term or short definition.
- A factor is selected that has no map visualization available.
- Raw attribution output contains prohibited or misleading factor labels that must be filtered or renamed.
- The same request is repeated while dataset versions and model or explainability configuration remain unchanged.

## Requirements *(mandatory)*

### Main Flow

1. The user requests an estimate and receives the result (UC-13; optionally UC-14).
2. The user selects an “Explain” / “Details” view for the returned estimate.
3. The system retrieves the feature values used for the estimate and the baseline value metadata.
4. The explainability service computes per-factor contributions (positive/negative) relative to the baseline-anchored estimate.
5. The system ranks the contributions and selects the top contributors (e.g., top 3–5 increases and top 3–5 decreases).
6. The system formats each factor into a user-friendly explanation item:
    * factor name (e.g., “Proximity to schools”)
    * measured value (e.g., “Nearest school: 0.8 km”)
    * impact direction (+/–) and magnitude (absolute or relative, depending on product decision)
7. The UI displays the ranked list, clearly separating “increases value” vs. “decreases value”, and provides access to related map layers when applicable (e.g., show nearby schools/parks).

### Alternate Flows

- **3a**: Feature values are missing or were computed with partial data
  - **3a1**: The system explains only the available factors and flags which categories were unavailable (e.g., “Crime data unavailable”).
- **4a**: Attribution computation not supported for the current model or request type
  - **4a1**: The system provides a simplified explanation (e.g., category-level signals: amenities, accessibility, green space) without numeric contributions.
  - **4a2**: The UI labels the explanation as qualitative.
- **6a**: A factor is difficult to explain (highly technical or derived)
  - **6a1**: The system uses a glossary term and shows a brief plain-language description.
  - **6a2**: The UI links to “Learn more” help content (if provided by the project).

### Exception/Error Flows

- **No explicit exception flow is defined in `UC-15.md` beyond the failed end condition.**

### Data Involved

- **Estimate result**: The returned estimate that the user chooses to explain.
- **Feature values**: The feature values used for the estimate.
- **Baseline value metadata**: Baseline-related metadata used to anchor the explanation.
- **Per-factor contributions**: Positive and negative contributions computed relative to the baseline-anchored estimate.
- **Top contributors**: The ranked subset of the highest positive and negative contributions selected for display.
- **Factor name**: The user-friendly factor label shown in the explanation.
- **Measured value**: Supporting values such as distance, count, or category shown with a factor.
- **Impact direction and magnitude**: The positive or negative direction and the absolute or relative magnitude shown for a factor.
- **Unavailable categories**: Flags for categories that could not be included in the explanation.
- **Simplified explanation**: Category-level signals returned when numeric attribution is unsupported.
- **Glossary term and plain-language description**: Explanation text used when a factor is too technical to present directly.
- **Related map layers**: Map context connected to applicable factors such as nearby schools or parks.

### Functional Requirements

- **FR-01-001**: The system MUST allow the user to open an explanation view for a returned estimate.
- **FR-01-002**: When the explanation view is requested, the system MUST retrieve the feature values used for the estimate and the baseline value metadata.
- **FR-01-003**: The explainability service MUST compute positive and negative per-factor contributions relative to the baseline-anchored estimate.
- **FR-01-004**: The system MUST rank contributions and select the configured top contributors for display, such as top increases and top decreases, using the configured default top-N count.
- **FR-01-005**: The system MUST format each explanation item with a factor name, a supporting measured value when applicable, and impact direction and magnitude.
- **FR-01-006**: The UI MUST display the ranked contributors in clearly separated "Increases value" and "Decreases value" sections or equivalent labels.
- **FR-01-007**: Each displayed factor MUST use a human-readable label and include at least one supporting value when applicable.
- **FR-01-008**: Each displayed factor MUST show impact direction, and any numeric magnitude shown MUST use the configured contribution format, be clearly labeled, and use consistent units and formatting.
- **FR-01-009**: The default explanation list MUST be limited to the configured top-N factors for each side, and the UI MUST enforce that configured default count.
- **FR-01-010**: Distances, units, and numeric values in explanation items MUST use consistent formatting and rounding rules.
- **FR-01-011**: When a simpler label exists for a factor, the UI MUST avoid highly technical jargon, or it MUST provide a definition or help affordance for that factor.
- **FR-01-012**: If feature values are missing or partial, the system MUST explain only the available factors, flag which categories are unavailable, and the UI MUST NOT present missing categories as zero impact or neutral values.
- **FR-01-013**: If numeric attribution is not supported for the current model or request type, the system MUST provide a simplified qualitative explanation without numeric contributions, and the UI MUST label the explanation as qualitative and note the limitation.
- **FR-01-014**: If the explainability service fails or times out, the UI MUST show a user-friendly explanation-unavailable message, keep the estimate visible and unchanged, and MUST NOT crash or block other estimate interactions.
- **FR-01-015**: If retry is supported for explanation failure, the UI MUST provide a retry action.
- **FR-01-016**: When a selected factor corresponds to real map context and a map layer is available, the UI MUST highlight the relevant map context, ensure the highlighted layer matches the selected factor category, and allow dismissal back to the prior map state without losing the explanation panel.
- **FR-01-017**: When a selected factor has no map visualization available, the UI MUST show factor details, MUST NOT attempt to display an invalid layer, and MUST indicate that map view is unavailable for that factor.
- **FR-01-018**: If policy-based filtering or renaming rules apply, the UI MUST NOT display prohibited factor labels as-is and MUST either omit the factor or display an approved renamed label.
- **FR-01-019**: If policy-based omission materially reduces explanation coverage, the UI MUST display a completeness note.
- **FR-01-020**: For repeated requests with unchanged dataset versions and model or explainability configuration, the top factors and their ordering MUST remain consistent except for ties handled by defined tie-breaking rules, and supporting values and units MUST remain consistent within rounding rules.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-15-01 | FR-01-001, FR-01-002, FR-01-003, FR-01-004, FR-01-005, FR-01-006, FR-01-007, FR-01-008, FR-01-009 |
| AT-15-02 | FR-01-003, FR-01-006, FR-01-008 |
| AT-15-03 | FR-01-005, FR-01-010, FR-01-011 |
| AT-15-04 | FR-01-012 |
| AT-15-05 | FR-01-013 |
| AT-15-06 | FR-01-014, FR-01-015 |
| AT-15-07 | FR-01-016 |
| AT-15-08 | FR-01-017 |
| AT-15-09 | FR-01-018, FR-01-019 |
| AT-15-10 | FR-01-020 |

#### Flow Steps or Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow Step 1 | FR-01-001 |
| Main Flow Step 2 | FR-01-001 |
| Main Flow Step 3 | FR-01-002, FR-01-012 |
| Main Flow Step 4 | FR-01-003, FR-01-013 |
| Main Flow Step 5 | FR-01-004, FR-01-009, FR-01-020 |
| Main Flow Step 6 | FR-01-005, FR-01-007, FR-01-008, FR-01-010, FR-01-011 |
| Main Flow Step 7 | FR-01-006, FR-01-016, FR-01-017, FR-01-018, FR-01-019 |
| Alternate Flow 3a | FR-01-012 |
| Alternate Flow 4a | FR-01-013 |
| Alternate Flow 6a | FR-01-011 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of successful explanation-supported test runs, the UI displays a ranked top-N list of factors separated into increases and decreases, with readable labels, impact direction, and supporting values when applicable.
- **SC-002**: In 100% of explanation-display test runs, factor signs, units, and numeric formatting remain internally consistent and do not contradict the displayed section labels.
- **SC-003**: In 100% of partial-data, unsupported-attribution, or explainability-failure test runs, the estimate remains visible and the UI presents the appropriate partial, qualitative, or unavailable explanation state without blocking other estimate interactions.
- **SC-004**: When factors are precomputed or cached, at least 95% of explanation views load within 2 seconds; otherwise explanation loading meets the configured service threshold.
- **SC-005**: In 100% of repeated-request test runs with unchanged data and explainability configuration, the displayed top factors, ordering, units, and supporting values remain consistent within rounding and tie-breaking rules.
