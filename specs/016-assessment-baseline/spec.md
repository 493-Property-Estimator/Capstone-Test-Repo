# Feature Specification: Use assessment baseline

**Feature Branch**: `016-assessment-baseline`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-16.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-16-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-16-AT.md Hard rules: 1) Copy the use case flows directly into spec.md (main + alternate + exception flows). Preserve ordering and intent. Do not invent steps. 2) You may make style/grammar improvements only if meaning is unchanged. 3) Extract functional requirements (FRs) ONLY from: - the flows in UC-16.md, and - the checks/expectations in UC-16-AT.md Do not add “nice-to-have” requirements that aren’t supported by those sources. 4) Keep implementation constraints: Python, vanilla HTML/CSS/JS. 5) Treat this use case as its own feature branch (branch naming suggestion is fine, but don’t actually run git commands unless asked). Spec contents required: - Feature name (from use case title) - Summary / goal - Actors - Preconditions - Triggers - Main flow (verbatim from use case) - Alternate flows (verbatim) - Exception/error flows (verbatim) - Data involved (only what the use case mentions) - Functional requirements list (numbered FR-01-001, FR-01-015, ...) - Traceability section mapping: - each acceptance test -> related FRs - each flow step (or flow section) -> related FRs (coarse mapping is fine) Output: - Update/produce the spec.md for this feature. If Spec-Kit expects a per-feature folder/file, follow the tool's convention, but the content must match the above constraints."

## Summary

Anchor each property estimate to an official assessment baseline, apply factor-based adjustments, and present the result with enough provenance and warning information for the estimate to be explainable and traceable.

## Goal

The estimate is anchored to an official assessment baseline, and adjustments from surrounding factors are applied so that the result is explainable and traceable.

## Actors

- **Primary Actor**: General User
- **Secondary Actors**: Assessment Data Store, Valuation Engine, Feature Store/Database, Explainability/Attribution Service

## Preconditions

- The user provided a property location that can be mapped to an assessment unit (parcel/address/assessment area).
- Assessment baseline data has been ingested and is available (e.g., municipal property assessment values for the project's target area).
- A baseline selection rule exists for ambiguous matches (e.g., multiple parcels near a clicked point).

## Trigger

The user requests an estimate for a property.

## User Scenarios & Testing

### User Story 1 - View a baseline-anchored estimate (Priority: P1)

As a general user, I want an estimate that starts from an official assessment baseline and shows the resulting adjusted value so I can interpret the estimate against a known starting point.

**Why this priority**: This is the core valuation behavior for UC-16 and the minimum feature slice that delivers user value.

**Independent Test**: Submit an estimate request for a property with baseline data and verify that the response and UI show the baseline value, the final estimate, and provenance metadata.

**Acceptance Scenarios**:

1. **Given** the user requests an estimate for a property with available baseline data, **When** the system returns a result, **Then** it includes the final estimate, baseline value, baseline provenance, and a baseline-plus-adjustments framing.
2. **Given** the system returns an adjustment breakdown, **When** the result is validated, **Then** the final estimate is consistent with the baseline plus the returned adjustments.

### User Story 2 - Understand assumptions and degraded cases (Priority: P2)

As a general user, I want the system to disclose ambiguous matching, missing or stale baselines, partial feature availability, and guardrail use so I can judge how reliable the estimate is.

**Why this priority**: The estimate must remain transparent when the normal flow is degraded or assumptions are required.

**Independent Test**: Exercise ambiguous-match, missing-baseline, stale-baseline, partial-feature, and guardrail cases and verify that the system returns and surfaces the appropriate warnings or errors.

**Acceptance Scenarios**:

1. **Given** the location maps to multiple assessment units, **When** the system selects a match, **Then** the selection is deterministic and the assumption is disclosed.
2. **Given** the baseline is missing or stale, **When** the system processes the request, **Then** it follows the configured policy and clearly communicates the limitation.
3. **Given** some feature categories are unavailable or guardrails are applied, **When** the estimate is returned, **Then** the result remains baseline-anchored when possible and the UI does not hide the reduced reliability.

### User Story 3 - Inspect traceability details (Priority: P3)

As a general user or support reviewer, I want stable provenance and request traceability details so the estimate can be inspected, repeated, and supported.

**Why this priority**: Provenance and repeatability make the output explainable and operationally supportable.

**Independent Test**: Repeat the same request with unchanged versions and verify stable provenance fields, stable baseline selection, and a usable correlation or request identifier.

**Acceptance Scenarios**:

1. **Given** a successful estimate response, **When** provenance is inspected, **Then** the response exposes the year, source, assessment unit identifier, and traceability identifier.
2. **Given** repeated requests with unchanged versions and configuration, **When** results are compared, **Then** baseline selection and provenance fields remain consistent within configured rounding rules.

### Edge Cases

- The location maps to multiple possible assessment units and the system must select one deterministically and disclose the assumption.
- The assessment baseline is missing, stale, or unavailable and the system must either fail clearly or use a disclosed fallback, depending on policy.
- Feature computation returns only partial results and the system must flag missing categories instead of implying zero impact.
- Guardrails cap an extreme deviation from baseline and the system must flag low confidence and the guardrail application.

## Main Flow

### Main Success Scenario

1. The user submits a property estimate request for a location.
2. The system normalizes the location and determines the assessment lookup key (e.g., parcel identifier, nearest parcel to point, or address match).
3. The system retrieves the assessment baseline value and metadata (assessment year, jurisdiction/source, identifier used).
4. The system computes the surrounding-factor feature values (amenities, accessibility, green space, crime, etc.) using available open data.
5. The valuation engine calculates per-factor adjustments to the baseline (additions/subtractions) based on the computed features and configured weights/model.
6. The valuation engine sums the baseline and adjustments to produce the final estimate.
7. The system returns the final estimate along with baseline metadata and (optionally) a baseline vs. adjusted breakdown suitable for explainability (UC-15).
8. The UI presents the baseline-anchored framing (e.g., “Assessment baseline + adjustments”) so the user can interpret the estimate as an adjustment from a known starting point.

## Alternate Flows

- **2a**: The location maps to multiple possible assessment units (ambiguous parcel)
  - 2a1: The system selects the best match using a deterministic rule (e.g., closest centroid) and flags that an assumption was made.
  - 2a2: If the UI supports it, the system asks the user to choose the correct parcel boundary.

## Exception/Error Flows

- **3a**: Assessment baseline data is unavailable or stale
  - 3a1: The system attempts a fallback (e.g., nearest assessment record, neighbourhood-level baseline) if allowed.
  - 3a2: The system warns that the estimate is less explainable due to baseline limitations.
  - 3a3: If policy forbids non-baseline estimates, the system returns an error and the UI instructs the user to try another location or later.
- **5a**: Feature computation returns partial results
  - 5a1: The system computes adjustments using only available factors and flags missing categories to the user (and to logs/metrics).
- **6a**: The final estimate is outside reasonable bounds compared to baseline (guardrail triggered)
  - 6a1: The system caps or reviews adjustment magnitude using configured thresholds.
  - 6a2: The system flags the result as low confidence and recommends providing more details or verifying the location.

## Data Involved

- Property location submitted by the user.
- Normalized location and assessment lookup key.
- Assessment baseline value.
- Baseline metadata: assessment year, jurisdiction/source, identifier used, and dataset version/refresh date when available.
- Surrounding-factor feature values such as amenities, accessibility, green space, and crime.
- Per-factor adjustments and optional total adjustment or baseline-vs-adjusted breakdown.
- Final estimate.
- Warning and status flags for assumptions, fallback use, baseline limitations, partial feature availability, and guardrail application.
- Timestamp and correlation/request identifier.
- Missing-feature categories.

## Requirements

### Functional Requirements

- **FR-01-001**: The system MUST accept a property estimate request for a user-supplied location.
- **FR-01-002**: The system MUST normalize the submitted location and determine an assessment lookup key for the estimate request.
- **FR-01-003**: The system MUST retrieve an assessment baseline value together with baseline metadata including assessment year, jurisdiction/source, and the identifier used for the match.
- **FR-01-004**: The system MUST compute surrounding-factor feature values using available data for the requested location.
- **FR-01-005**: The system MUST calculate factor-based adjustments to the assessment baseline from the computed features.
- **FR-01-006**: The system MUST derive the final estimate from the assessment baseline plus the computed adjustments and MUST not return a breakdown that contradicts the returned estimate within configured rounding rules.
- **FR-01-007**: The system MUST return the final estimate together with the baseline value and baseline metadata in the estimate response.
- **FR-01-008**: The system MUST present the estimate in the UI using a baseline-plus-adjustments framing rather than only a single opaque number.
- **FR-01-009**: The system MUST make baseline provenance reachable from the estimate result view, including the assessment year, jurisdiction/source dataset, and assessment unit identifier used for the match.
- **FR-01-010**: When a location maps to multiple possible assessment units, the system MUST apply a configured deterministic selection rule, repeat the same selection for the same unchanged input, and disclose that an assumption was made.
- **FR-01-011**: When no assessment baseline record exists or baseline data is stale or unavailable, the system MUST follow the configured policy by either failing clearly without returning an estimate and instructing the user to try another location or later, or returning a fallback-based estimate with an explicit reduced-provenance warning.
- **FR-01-012**: When the system returns a fallback-based estimate, the UI MUST not present the result as though it came from the normal official baseline and MUST identify the fallback type if available.
- **FR-01-013**: When feature computation returns partial results, the system MUST continue to anchor the estimate to the baseline when the baseline is available, include missing-feature flags identifying unavailable categories, and show a completeness warning that does not imply missing features had zero impact.
- **FR-01-014**: When guardrails or caps are applied to limit an extreme deviation from baseline, the system MUST flag that guardrails were applied, surface a low-confidence or equivalent indicator, and keep baseline provenance inspectable.
- **FR-01-015**: The system MUST include a timestamp and a correlation or request identifier in the successful response when supported, or otherwise ensure an equivalent identifier is recorded and tied to the user session for traceability.
- **FR-01-016**: The system MUST keep baseline provenance fields stable and usable for support and debugging across repeated requests when dataset versions, baseline data, and model configuration are unchanged.

### Non-Functional Requirements

- **NFR-01**: Under normal load, baseline lookup and adjustment computation MUST meet the agreed latency target for this feature.
- **NFR-02**: Baseline unavailability and partial feature outages MUST produce explicit non-crashing warning or failure states consistent with the configured policy.
- **NFR-03**: Users MUST be able to inspect baseline provenance and understand when assumptions, fallbacks, or guardrails affected the result.

### Key Entities

- **Estimate Request**: A request for a property estimate based on a user-supplied location and the resulting normalized lookup information.
- **Assessment Baseline**: The official baseline valuation record used as the starting point for the estimate, including provenance metadata.
- **Factor Adjustment**: A positive or negative value derived from surrounding-factor features and applied to the baseline.
- **Estimate Result**: The returned output containing the final estimate, baseline information, optional breakdown, warnings, and traceability fields.

## Success Criteria

### Measurable Outcomes

- **SC-01**: In 100% of successful baseline-anchored estimate responses, the user can inspect the baseline value, assessment year, source/jurisdiction, and matched assessment unit identifier from the estimate context.
- **SC-02**: In 100% of successful responses that include an adjustment breakdown, the returned final estimate is mathematically consistent with the baseline plus the returned adjustment values within configured rounding rules.
- **SC-03**: In 100% of ambiguous-match, fallback, stale-baseline, partial-feature, and guardrail test cases, the user sees a specific warning or error describing the limitation rather than a generic failure message.
- **SC-04**: With unchanged dataset versions, baseline data, and model configuration, repeated requests for the same input produce the same baseline selection and stable provenance fields in 100% of repeatability tests.

## Assumptions

- The scenario file was used only to clarify terminology and presentation details; use case and acceptance test files remain the source of truth.
- The feature may return either a hard failure or a disclosed fallback estimate when the baseline is unavailable, because the configured policy is intentionally left open by the source material.

## Traceability

### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-16-01 | FR-01-003, FR-01-007, FR-01-009, FR-01-015 |
| AT-16-02 | FR-01-007, FR-01-008, FR-01-009 |
| AT-16-03 | FR-01-005, FR-01-006 |
| AT-16-04 | FR-01-009, FR-01-010 |
| AT-16-05 | FR-01-011, FR-01-012 |
| AT-16-06 | FR-01-011 |
| AT-16-07 | FR-01-013 |
| AT-16-08 | FR-01-014 |
| AT-16-09 | FR-01-009, FR-01-015, FR-01-016 |
| AT-16-10 | FR-01-010, FR-01-016 |

### Flow Steps and Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow 1 | FR-01-001 |
| Main Flow 2 | FR-01-002 |
| Main Flow 3 | FR-01-003 |
| Main Flow 4 | FR-01-004 |
| Main Flow 5 | FR-01-005 |
| Main Flow 6 | FR-01-006 |
| Main Flow 7 | FR-01-007, FR-01-015 |
| Main Flow 8 | FR-01-008, FR-01-009 |
| Alternate Flow 2a | FR-01-010 |
| Exception Flow 3a | FR-01-011, FR-01-012 |
| Exception Flow 5a | FR-01-013 |
| Exception Flow 6a | FR-01-014 |
