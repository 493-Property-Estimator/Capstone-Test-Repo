# Acceptance Tests — UC-16: Use assessment baseline

## Purpose
Verify that the system anchors each estimate to an official assessment baseline, applies factor-based adjustments, and returns enough baseline provenance metadata for the result to be explainable and traceable. Verify safe, transparent behavior for ambiguous parcel matches, missing/stale baselines, partial feature availability, and guardrail-triggered results.

## References
* User Story: **US-16: Use assessment baseline**
* Use Case: `Use Cases/UC-16.md`
* Scenario: `Scenarios/SC-UC-16.md`
* Related Use Case: `Use Cases/UC-13.md` (point estimate)
* Related Use Case: `Use Cases/UC-15.md` (explanation of adjustments, optional)

## Assumptions (minimal)
* The estimate API returns a point estimate and includes baseline metadata when the request is baseline-anchored.
* The UI displays estimates using “baseline + adjustments” framing (or an equivalent representation).
* The product has an explicit policy for baseline unavailability:
  * **Policy A**: fail request (no estimate), **or**
  * **Policy B**: allow fallback baseline (with reduced provenance warning).
  These tests validate whichever policy is configured for the environment under test.

## Test Data Setup
Define controlled locations and configurations for repeatable tests:
* **L1 (Normal)**: Location with a single unambiguous assessment unit match; baseline available; full features available.
* **L2 (Ambiguous match)**: Location that maps to multiple assessment units (e.g., point near parcel boundary); deterministic selection rule should apply.
* **L3 (Baseline missing)**: Location with no assessment baseline record (or forced simulation of missing baseline).
* **L4 (Baseline stale/unavailable)**: Location where baseline dataset access is degraded (stale version, fetch error, or forced “stale” flag).
* **L5 (Partial features)**: Location where at least one feature category is unavailable/timeouts are forced.
* **L6 (Guardrail case)**: Location/configuration that would produce an extreme adjustment relative to baseline without guardrails.
* Baseline dataset provenance (expected assessment year/source/jurisdiction) is known for **L1/L2** so it can be verified.

## Acceptance Test Suite (Gherkin-style)

### AT-16-01 — Return baseline-anchored estimate with provenance (happy path)
**Given** the user requests an estimate for **L1**  
**And** baseline assessment data is available for **L1**  
**When** the system returns an estimate response  
**Then** the response contains `estimated_value`  
**And** the response contains a baseline value field (e.g., `baseline_value`)  
**And** the response contains baseline provenance metadata sufficient for inspection, including:
* assessment year
* jurisdiction/source dataset identifier/name  
* the assessment unit identifier/key used for the match (e.g., parcel ID)  
**And** the response includes a `timestamp` and a correlation/request identifier (if supported).

### AT-16-02 — UI uses “baseline + adjustments” framing
**Given** the user views an estimate result for **L1**  
**When** the UI renders the result  
**Then** the UI displays the assessment baseline value and the final estimated value  
**And** the UI presents the estimate as “baseline + adjustments” (or equivalent) rather than only a single opaque number  
**And** baseline provenance (year/source/unit identifier) is reachable from the result view without leaving the estimate context.

### AT-16-03 — Consistency: estimate is derived from baseline plus adjustments (when breakdown is provided)
**Given** the response for **L1** includes any adjustment breakdown field(s) (e.g., `total_adjustment` and/or per-factor adjustments)  
**When** the user (or test harness) validates the returned numbers  
**Then** the displayed/returned final estimate is consistent with baseline anchoring, such as:
* `estimated_value = baseline_value + total_adjustment` (when `total_adjustment` is provided), **or**
* `estimated_value = baseline_value + sum(per_factor_adjustments)` (when per-factor adjustments are provided)  
**And** the system does not return an estimate that contradicts its own breakdown (within rounding rules).

### AT-16-04 — Ambiguous assessment unit match is deterministic and disclosed
**Given** the user requests an estimate for **L2** where multiple assessment units can match  
**When** the system selects an assessment unit  
**Then** the system uses the configured deterministic selection rule (repeat requests choose the same unit for the same input)  
**And** the response includes a warning/flag indicating that an assumption was made (e.g., “Multiple parcels matched; selected closest”)  
**And** the UI surfaces that warning in a non-blocking way  
**And** the baseline provenance metadata reflects the selected unit identifier.

### AT-16-05 — Baseline missing behavior matches configured policy (fail or fallback)
**Given** the user requests an estimate for **L3** where no baseline record exists  
**When** the system processes the request  
**Then** the system follows the configured baseline-missing policy:
* **Policy A (fail)**: no `estimated_value` is returned and the UI shows a clear error indicating baseline is unavailable, **or**
* **Policy B (fallback)**: an `estimated_value` is returned with a clear warning that a fallback baseline was used, including the fallback type if available (e.g., nearest-neighbour or neighbourhood-level).  
**And** under **Policy B**, the UI does not present fallback results as if they were sourced from the normal official baseline.

### AT-16-06 — Baseline stale/unavailable is explicitly flagged
**Given** baseline access is stale/degraded for **L4**  
**When** the system returns a response (estimate or error, depending on policy)  
**Then** the user receives an explicit warning/error explaining baseline limitations (e.g., stale version or unavailable source)  
**And** the UI does not hide baseline limitations behind generic “Something went wrong” messaging.

### AT-16-07 — Partial feature availability still anchors to baseline and flags missing categories
**Given** the user requests an estimate for **L5** where some feature categories are missing/unavailable  
**When** the system returns the estimate  
**Then** the response remains baseline-anchored (baseline value + provenance is present) if baseline is available  
**And** the response includes missing-feature flags identifying which categories were unavailable  
**And** the UI displays a completeness warning and does not imply missing features had zero impact.

### AT-16-08 — Guardrail-triggered estimate is valid and transparent
**Given** the user requests an estimate for **L6** that would produce an extreme deviation from baseline without guardrails  
**When** the valuation engine applies guardrails/caps  
**Then** the response includes a clear “guardrail applied” warning/flag  
**And** the UI surfaces a low-confidence (or similar) indicator consistent with product requirements  
**And** the estimate remains baseline-anchored and the user can still inspect baseline provenance.

### AT-16-09 — Provenance and traceability metadata is stable and usable for support/debugging
**Given** the user requests an estimate for **L1**  
**When** the system returns a successful response  
**Then** the response includes a correlation/request identifier (or the system logs one tied to the user session)  
**And** baseline provenance (year/source/unit identifier, and dataset version/refresh date if tracked) is present in the response and/or UI  
**And** repeating the same request with unchanged dataset/model versions yields consistent baseline provenance fields.

### AT-16-10 — Repeatability: fixed versions yield consistent baseline selection and baseline-anchored estimate
**Given** the user requests estimates for **L1** (and **L2**) multiple times  
**And** dataset versions, baseline assessment data, and model configuration are unchanged between runs  
**When** results are returned  
**Then** the baseline selection is consistent (same assessment unit chosen for the same input)  
**And** the returned baseline provenance fields remain consistent (within rounding/formatting rules)  
**And** the returned estimate remains baseline-anchored and consistent within configured rounding rules.

## Non-Functional Acceptance Criteria (verifiable)
* **Performance**: Baseline lookup + adjustment computation meets an agreed latency target under normal load (e.g., p95 ≤ 3s for cached features).
* **Reliability**: Baseline unavailability and partial feature outages produce explicit, non-crashing failure/warning states consistent with configured policy.
* **Transparency**: Users can inspect baseline provenance (year/source/unit identifier) and see when assumptions/guardrails/fallbacks were used.
