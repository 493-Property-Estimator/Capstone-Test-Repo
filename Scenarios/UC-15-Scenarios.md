# Scenario — UC-15: Show top contributing factors

## Scenario Name
Understand why the estimate differs from baseline

## Narrative
Sam gets an estimated value for a property in Edmonton and notices it is meaningfully higher than the assessment baseline. Sam wants to understand *why* the system adjusted the value—without reading a long report. Sam opens a “Why this value?” view and expects a short ranked list of the biggest factors that increased the estimate and the biggest factors that decreased it, with plain-language labels and a few supporting details (e.g., distances to parks/schools). If a factor is tied to map-based context, Sam wants to be able to see it on the map (e.g., nearby schools or parks).

## Scope
Property Value Estimator (PVE) system (Web UI + Estimate API + Explainability/Attribution service + Feature Store/Data Stores)

## Actors
* **Primary Actor**: General User (Sam)
* **Supporting Actors**:
  * Web UI (results + “Why this value?” panel)
  * Estimate API (returns estimate + explanation payload or reference)
  * Location Normalization (address → canonical location)
  * Assessment Data Store (baseline value + metadata)
  * Feature Store / Open-Data Services (feature retrieval/compute)
  * Valuation Engine (produces baseline-anchored estimate)
  * Explainability / Attribution Service (computes per-factor contributions)
  * Map UI Layers (optional visualization of factor-related context)
  * Logging/Monitoring (correlation IDs, explanation coverage flags)

## Preconditions
* A point estimate has been computed for the requested location (UC-13) and is available in the UI.
* The system has retained (or can recompute deterministically) the feature values used for valuation for this estimate.
* The system has a defined method for factor contributions (e.g., linear adjustments, feature attribution scores, SHAP-like values).
* Baseline metadata (assessment year/source) is available for anchoring the explanation.

## Trigger
The user requests the explanation view for a returned estimate (e.g., clicks/expands “Why this value?” or “Details”).

## Main Flow (Success Scenario)
1. Sam searches for an address and requests an estimate.
2. The UI displays the point estimate (and optionally an uncertainty range if available) with baseline metadata (assessment year/source).
3. Sam clicks “Why this value?”.
4. The system retrieves the estimate context for the request:
   * baseline value and metadata
   * the feature values used (or a reference to retrieve them)
   * the model/version used for valuation
5. The explainability service computes per-factor contributions relative to the baseline-anchored estimate, producing a set of factors with:
   * contribution sign (increases vs decreases)
   * contribution magnitude (dollars or normalized score, per product decision)
   * supporting measured values (e.g., “Nearest park: 300 m”)
6. The system ranks factors by absolute contribution magnitude and selects the top contributors (e.g., 3–5 increases and 3–5 decreases).
7. The system formats each factor into user-friendly explanation items, including:
   * short label (e.g., “Proximity to parks”)
   * supporting value(s) (e.g., “Nearest park: 0.3 km”)
   * impact direction and magnitude (e.g., “↑ $12k” or “↑ High” depending on configuration)
8. The UI displays the explanation panel with two clearly labeled sections:
   * **Increases value**
   * **Decreases value**
   Each section shows a ranked list of factors.
9. Sam clicks one factor (e.g., “Proximity to schools”).
10. If supported, the UI highlights the relevant context on the map (e.g., nearest school markers and distance), and the explanation panel remains visible.
11. Sam uses the factor list to interpret the estimate and decide whether to trust it, investigate further, or compare a different property.

## Postconditions (Success)
* The user sees a short ranked list of top positive and negative contributing factors with readable labels and supporting values.
* The system logs explanation coverage (which factors were available, which were missing) and any warnings with a correlation ID.

## Variations / Extensions
* **4a — Feature values missing or partial**
  * 4a1: The system returns explanations for available factors only.
  * 4a2: The explanation payload includes missing-category flags (e.g., “Crime data unavailable”).
  * 4a3: The UI displays “Not available” for missing categories and avoids implying a neutral/zero impact.
* **5a — Attribution not supported for the current model/request**
  * 5a1: The system returns a simplified, qualitative explanation (e.g., category-level signals such as amenities, accessibility, green space).
  * 5a2: The UI labels the explanation as qualitative (no numeric impacts) and provides a brief note describing the limitation.
* **6a — A factor is too technical to present directly**
  * 6a1: The system uses a plain-language label and a short definition from a glossary (if available).
  * 6a2: The UI offers “Learn more” for factor definitions and limitations.
* **7a — Top factors include sensitive or misleading signals**
  * 7a1: The system applies policy-based filtering/renaming to avoid presenting prohibited or confusing factor labels.
  * 7a2: The UI continues to show a usable list of remaining top factors with a completeness note if filtering reduces the list.
* **9a — Map layer not available for a selected factor**
  * 9a1: The UI shows the factor details (supporting values) but disables map highlighting for that factor.
  * 9a2: The UI indicates “Map view not available for this factor” without failing the explanation panel.
* **10a — User wants more than the default number of factors**
  * 10a1: Sam clicks “Show more factors”.
  * 10a2: The UI reveals additional ranked factors (or a scrollable list), with the same labeling and metadata conventions.

## Data Examples (Illustrative)
Example explanation output (numbers are illustrative only; magnitude format depends on product decision):
* Baseline (assessment): `$430,000` (Year: `2024`, example)
* Point estimate: `$452,000`
* Increases value (top):
  * Proximity to parks — Nearest park: `0.3 km` — `↑ $12k`
  * School accessibility — Nearest school: `0.8 km` — `↑ $7k`
  * Transit access — Nearest stop: `0.2 km` — `↑ $4k`
* Decreases value (top):
  * Distance to employment centers — Downtown: `9.5 km` — `↓ $6k`
  * Limited green space coverage (area-level) — `↓ $3k`

## Notes / Assumptions
* “Top contributing factors” are shown relative to the baseline-anchored estimate so the explanation is coherent.
* The system should present factors as explanatory aids, not as definitive causal claims; UI should avoid overconfident language.
* Factor labels, units, and rounding should be consistent across properties to support quick comparison.

