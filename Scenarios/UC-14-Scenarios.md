# Scenario — UC-14: Return a low/high range

## Scenario Name
Understand uncertainty with a low/high estimate range

## Narrative
Riley is deciding whether to make an offer on a home in Edmonton. A single estimate is useful, but Riley worries about over-trusting one number—especially for properties that might be unusual or in fast-changing areas. Riley uses the Property Value Estimator (PVE) to get an estimate and wants to see a clear low/high range that communicates uncertainty, so they can judge whether the listing price is plausibly in line with the estimate or if the result is too uncertain to rely on without further research.

## Scope
Property Value Estimator (PVE) system (Web UI + Estimate API + Valuation Engine + Feature Store/Data Stores)

## Actors
* **Primary Actor**: General User (Riley)
* **Supporting Actors**:
  * Web UI (map + results)
  * Estimate API (or equivalent backend endpoint)
  * Location Normalization (address → canonical location)
  * Assessment Data Store (assessment baseline lookup)
  * Feature Store / Open-Data Services (feature retrieval/compute)
  * Valuation Engine (point estimate + uncertainty/range computation)
  * Logging/Monitoring (correlation IDs, range warnings)

## Preconditions
* Preconditions for producing a point estimate are satisfied (see UC-13).
* The valuation engine has a defined approach to compute uncertainty (e.g., prediction interval, residual-based band, comparable variance).
* The UI has a way to display the range near the point estimate with a clear label and disclaimer.

## Trigger
The user requests an estimate and chooses to view the uncertainty range (or the system automatically includes the range in the results).

## Main Flow (Success Scenario)
1. Riley opens the PVE web app and searches for a property address (or selects a point on the map).
2. The system normalizes the input to a canonical location and validates optional attributes if provided.
3. Riley clicks “Estimate” (or “Estimate with range” if the UI provides an explicit option).
4. The system retrieves the assessment baseline for the canonical location and captures baseline metadata (year/source).
5. The system retrieves and/or computes open-data features required for valuation within configured time limits.
6. The valuation engine computes a point estimate for the property value.
7. The valuation engine computes an uncertainty measure using the configured approach (e.g., an 80% or 90% interval, depending on product configuration).
8. The system converts the uncertainty measure into a currency-formatted low/high range and applies guardrails (ordering, rounding, non-negative low).
9. The Estimate API returns a response containing:
   * `estimated_value` (point estimate)
   * `low_estimate` and `high_estimate` (range bounds)
   * `range_type` / minimal range metadata (e.g., “prediction interval” or “confidence band”, per product wording)
   * `timestamp`, location summary, and baseline metadata
   * any non-blocking warnings (e.g., missing features, range adjusted)
10. The UI displays:
   * the point estimate prominently
   * the low/high range immediately adjacent, clearly labeled as a range (not a guarantee)
   * a brief disclaimer explaining the range is an uncertainty band and not a firm bound
11. Riley compares the listing price to the range:
   * If the listing price is within the range, Riley treats the estimate as plausible and continues evaluating.
   * If the listing price is far outside the range, Riley flags the listing for closer review (e.g., verify property details or neighborhood context).

## Postconditions (Success)
* The user sees a point estimate and a low/high range tied to the requested location and timestamp.
* The system logs the computation including any warnings (e.g., “range adjusted”, “partial features”) with a correlation ID for traceability.

## Variations / Extensions
* **7a — Insufficient data to compute a reliable range**
  * 7a1: The system returns the point estimate but omits the range.
  * 7a2: The response includes a warning such as “Range unavailable due to insufficient data.”
  * 7a3: The UI suggests actions to improve reliability (e.g., provide more property attributes if supported, or try again later).
* **7b — Range computation fails due to internal error**
  * 7b1: The system logs the error and returns the point estimate without a range (preferred graceful degradation), unless the product requires range as mandatory.
  * 7b2: The UI shows a non-blocking warning (“Range temporarily unavailable”) and keeps the point estimate visible.
* **8a — Invalid range produced (low > high, negative low, unreasonably wide)**
  * 8a1: The system applies guardrails (swap if needed, clamp low at zero, cap width or recompute using a safe fallback band).
  * 8a2: The system includes a “range adjusted” warning in the response.
  * 8a3: The UI displays a subtle note (e.g., “Range adjusted for stability”) to preserve transparency.
* **9a — Some features unavailable**
  * 9a1: The system returns a point estimate and range if possible, but flags reduced reliability.
  * 9a2: If missing features prevent range calculation, the system follows **7a** (point estimate only).
* **10a — User wants more explanation of the range**
  * 10a1: Riley clicks an “What does this range mean?” info icon.
  * 10a2: The UI shows a short explanation of the range type (e.g., configured interval level) and key limitations (data lag, missing features).

## Data Examples (Illustrative)
Example outputs for one property (numbers are illustrative only):
* Point estimate: `$452,000`
* Range: `$415,000` to `$492,000`
* Range label: “Estimated range” (e.g., “confidence band”, per product wording)
* Timestamp: `2026-02-12T18:25:00Z` (example)
* Warnings: `[]` (or `["Some features missing"]`, `["Range adjusted"]`)

## Notes / Assumptions
* The range is intended to communicate uncertainty and should be clearly labeled to avoid being interpreted as a guaranteed bound.
* The chosen interval level (e.g., 80%/90%/95%) and the wording used in the UI are product decisions and must be consistent across the application.
* Guardrails should prevent nonsensical ranges from being shown while still being transparent when adjustments occur.

