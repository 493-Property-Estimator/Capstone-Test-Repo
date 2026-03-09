# Scenario — UC-16: Use assessment baseline

## Scenario Name
Anchor the estimate to an official assessment baseline

## Narrative
Taylor is evaluating a property in Edmonton and wants an estimate they can *reason about* and defend in conversation. Taylor trusts official assessment data as a concrete starting point and expects the estimator to:
* start from an assessment baseline tied to a specific assessment unit (parcel/address record), with provenance (year/source/version)
* apply *explicit* adjustments based on surrounding open-data factors (amenities, accessibility, green space, etc.)
* disclose assumptions (e.g., ambiguous parcel match) and guardrails (e.g., capped adjustments) so the result remains explainable and traceable

## Scope
Property Value Estimator (PVE) system (Web UI + Estimate API + Valuation Engine + Assessment Baseline Data + Explainability support)

## Actors
* **Primary Actor**: General User (Taylor)
* **Supporting Actors**:
  * Web UI (estimate results + baseline details)
  * Location Normalization (address/map click → canonical location)
  * Assessment Lookup/Matching (location → assessment unit key)
  * Assessment Data Store (baseline value + metadata)
  * Feature Store / Open-Data Services (compute surrounding-factor features)
  * Valuation Engine (baseline + adjustments → final estimate)
  * Explainability/Attribution Service (optional breakdown for “baseline + adjustments”)
  * Logging/Monitoring (correlation IDs, baseline-match assumptions, guardrail flags)

## Preconditions
* The user provides a location that can be mapped to an assessment unit (parcel/address/assessment area).
* Assessment baseline data for the target jurisdiction is ingested and queryable.
* A deterministic rule exists for selecting an assessment unit when multiple candidates match a point/address.
* The system has configured adjustment weights/models and guardrails for extreme deviations from baseline.

## Trigger
The user requests an estimate for a property location.

## Main Flow (Success Scenario)
1. Taylor opens the PVE web app and searches for an address (or clicks a location on the map).
2. The system normalizes the location into a canonical representation (normalized address and/or coordinates).
3. The system determines the assessment lookup key by matching the canonical location to an assessment unit (e.g., parcel identifier).
4. The system retrieves the assessment baseline value and baseline metadata, such as:
   * assessment year
   * jurisdiction/source dataset
   * assessment unit identifier used (e.g., parcel ID)
   * dataset version and/or last refresh timestamp (if tracked)
5. The system computes surrounding-factor feature values using available open data sources (e.g., distances to parks/schools/transit, accessibility measures, area-level indicators).
6. The system validates feature completeness for the request (e.g., required vs optional factor sets) and notes any missing datasets.
7. The valuation engine calculates per-factor adjustments to the baseline based on the computed features and configured model/weights.
8. The valuation engine applies guardrails to ensure the result remains within reasonable bounds relative to the baseline (e.g., caps total adjustment magnitude and flags low confidence when capped).
9. The valuation engine sums **baseline + adjustments** to produce the final point estimate (and optional uncertainty range if enabled).
10. The Estimate API returns a response containing:
   * final estimate (`estimated_value`)
   * baseline value and baseline metadata (`baseline_value`, year/source, unit identifier)
   * optional breakdown elements suitable for explainability (e.g., total adjustments, or factor list used by UC-15)
   * warnings/flags if any assumptions, missing data, or guardrails were applied
   * timestamp and correlation/request identifier
11. The UI displays the estimate with baseline-anchored framing, for example:
   * “Assessment baseline (2024): $430,000”
   * “Adjustments: +$22,000”
   * “Estimated value: $452,000”
12. The UI shows lightweight “data health” indicators where applicable (e.g., “All datasets available” vs “Some datasets missing”, and whether guardrails were applied).
13. Taylor expands “Baseline details” to inspect the baseline metadata (year/source/version and the assessment unit used).
14. If the UI supports it, Taylor can copy/share a short “Provenance” summary (baseline year/source/unit + request timestamp/correlation ID) for traceability.
15. Taylor optionally opens “Why this value?” to view the top contributing factors that drove the adjustments (UC-15).

## Postconditions (Success)
* The user can see that the estimate is anchored to an assessment baseline and can inspect baseline provenance metadata.
* The system logs baseline matching, dataset versions, and any guardrail/assumption flags with a correlation ID for traceability.

## Variations / Extensions
* **3a — Ambiguous assessment unit match (multiple parcels/candidates)**
  * 3a1: The system selects the best match using a deterministic rule (e.g., closest parcel centroid to the chosen point).
  * 3a2: The response includes a warning such as “Multiple parcels matched; selected closest parcel.”
  * 3a3: If supported, the UI offers a way to confirm/choose a different parcel boundary and re-run the estimate.
* **4a — Baseline unavailable or stale**
  * 4a1: If policy allows, the system falls back to a nearest-neighbour baseline or neighbourhood-level baseline.
  * 4a2: The response includes a warning that baseline provenance is reduced and explainability may be limited.
  * 4a3: If policy forbids non-baseline estimates, the system returns an error and the UI instructs the user to try another location or later.
* **5a — Partial feature computation**
  * 5a1: The system computes adjustments using available factors only.
  * 5a2: The response includes missing-feature flags and a reduced-reliability warning.
  * 5a3: The UI shows a completeness note (e.g., “Some datasets unavailable; adjustments may be incomplete.”).
* **6a — Guardrail triggered due to extreme deviation from baseline**
  * 6a1: The system caps total adjustment magnitude according to configured thresholds and/or recomputes using conservative settings.
  * 6a2: The response includes a “guardrail applied” warning and a low-confidence indicator.
  * 6a3: The UI explains that the estimate may be less reliable and suggests providing more property details (if supported) or verifying the location.
* **10a — User requests baseline provenance details**
  * 10a1: Taylor clicks an info icon next to the baseline.
  * 10a2: The UI shows dataset name, year, and update cadence (if tracked), plus the assessment unit identifier used.
* **11a — User questions a large adjustment**
  * 11a1: Taylor clicks “Adjustments” to expand a breakdown view.
  * 11a2: The UI shows a short summary (e.g., “Top factors increased value by +$X, decreased by -$Y”) and offers “Why this value?” (UC-15).
  * 11a3: If guardrails were applied, the UI explains that adjustments were capped and marks the estimate as lower confidence.

## Business Rules / Guardrails (Product Requirements)
* The returned estimate must be baseline-anchored (baseline value is present and used in the computation), unless an explicit fallback policy is enabled and clearly disclosed.
* Baseline provenance must be inspectable: assessment year, source/jurisdiction, and the assessment unit key used for matching (plus dataset version/refresh date when available).
* Ambiguity in matching must be handled deterministically and disclosed to the user (and logged).
* Guardrails must not silently alter the estimate: if capping/conservative mode is used, the response/UI must indicate this.
* If required datasets are missing, the system must disclose reduced completeness rather than implying “zero impact”.

## Data Examples (Illustrative)
Example baseline-anchored result (numbers are illustrative only):
* Baseline:
  * Baseline value: `$430,000`
  * Assessment year: `2024`
  * Source: `Municipal Assessment Dataset` (example)
  * Assessment unit: `Parcel ID: 123-456-789` (example)
* Adjustments:
  * Total adjustments: `+$22,000`
  * Missing features: `[]` (or `[crime, routing]` depending on availability)
* Final:
  * Estimated value: `$452,000`
  * Timestamp: `2026-02-12T18:30:00Z` (example)
  * Warnings: `[]` (or `["Multiple parcels matched; selected closest"]`, `["Guardrail applied"]`)

## Acceptance Criteria (Checklist)
* The estimate response includes `baseline_value` and baseline metadata (year/source/unit identifier).
* The UI shows the estimate as “baseline + adjustments” (not just a single opaque number).
* Baseline provenance can be opened/inspected from the UI in ≤2 clicks.
* If multiple assessment units match, the system selects deterministically and returns a warning indicating an assumption.
* If baseline is unavailable and fallback is disabled, the user receives a clear error (no silent non-baseline estimate).
* If baseline fallback is enabled, the user sees the fallback type and reduced-provenance warning.
* If guardrails cap adjustments, the user sees a “guardrail applied” warning and a lower-confidence indicator.
* If feature computation is partial, the response lists missing categories and the UI displays a completeness note.
* The system logs correlation ID + baseline match details + dataset versions for traceability.

## Notes / Assumptions
* The baseline is the starting point for the estimate; the UI should consistently communicate “baseline + adjustments” to support explainability.
* When the system makes deterministic assumptions (e.g., parcel selection), it should disclose them in a lightweight way.
* Guardrails should prevent extreme outputs while preserving transparency that adjustments were capped or constrained.
