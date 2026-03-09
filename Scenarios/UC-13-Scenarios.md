# Scenario — UC-13: Return a single estimated value

## Scenario Name
Get a fast, single-value estimate for a specific property

## Narrative
Casey is relocating to Edmonton and is shortlisting homes to tour over the weekend. Casey doesn’t need a full report yet—they want one clear, easy-to-compare estimate for each listing they find online. Casey opens the Property Value Estimator (PVE), enters an address from a listing, optionally adds a couple of basic attributes (beds/baths and approximate size), and expects the system to return a single estimated value that can be used as a quick sanity check before spending time digging deeper.

## Scope
Property Value Estimator (PVE) system (Web UI + Estimate API + Location Normalization + Feature/Valuation services + Data Stores)

## Actors
* **Primary Actor**: General User (Casey)
* **Supporting Actors**:
  * Web UI (map + form)
  * Location Normalization / Geocoding (address → canonical location)
  * Assessment Data Store (assessment baseline lookup)
  * Feature Store / Open-Data Services (retrieval/compute of open-data features)
  * Valuation Engine (applies adjustments to baseline)
  * Logging/Monitoring (correlation IDs, latency/error metrics)

## Preconditions
* The UI and Estimate API are reachable.
* The user can provide a property location (address, coordinates, or map click).
* Baseline assessment data is available for the area, or a fallback policy exists for missing baseline.
* At least some open-data features are available, or the valuation engine can run in a reduced-feature mode.

## Trigger
The user submits an estimate request (e.g., clicks “Estimate” after providing a location).

## Main Flow (Success Scenario)
1. Casey opens the PVE web app and sees an address search bar and an “Estimate” form.
2. Casey enters an address (e.g., `10950 97 St NW, Edmonton, AB`) and selects the best match from autocomplete.
3. The UI places a marker on the map and fills the selected address into the form.
4. (Optional) Casey enters a couple of basic attributes from the listing:
   * bedrooms: `3`
   * bathrooms: `2`
   * approximate size: `1500 sq ft` (if supported)
5. Casey clicks “Estimate”.
6. The system validates the request (required fields present; address/coordinates usable; numeric fields in valid ranges if provided).
7. The system normalizes the input to a canonical location and determines a representative point/parcel association for data retrieval.
8. The system retrieves the assessment baseline for the canonical location (or nearest applicable assessment unit) and records baseline metadata (source, year).
9. The system retrieves and/or computes relevant open-data features for the location (e.g., proximity-based features, area-level signals, accessibility proxies), within configured time limits.
10. The valuation engine computes a single estimated value using the baseline plus factor adjustments derived from the available features (and optional user-provided attributes if supported by the model).
11. The Estimate API returns a response containing:
   * `estimated_value` (single number in local currency)
   * `location_summary` (normalized address / coordinates)
   * `timestamp`
   * `baseline_metadata` (assessment year/source) and any non-blocking warnings
12. The UI displays the estimated value prominently (e.g., “Estimated value: $452,000”) along with a small “as of” timestamp and a brief disclaimer (e.g., “Not an appraisal”).
13. Casey records the value for comparison and optionally repeats the flow for another address.

## Postconditions (Success)
* The user sees one clear estimated value associated with the requested location and timestamp.
* The system logs the request/response metadata (excluding sensitive user data) with a correlation ID for monitoring and debugging.

## Variations / Extensions
* **6a — Request validation fails**
  * 6a1: The API returns a structured validation error (e.g., “Size must be positive”, “Address required”).
  * 6a2: The UI highlights the invalid field(s) and keeps the user’s inputs so they can correct and resubmit.
* **7a — Address cannot be normalized**
  * 7a1: The UI shows “Address not found” (or ambiguity) and suggests selecting from alternate matches.
  * 7a2: The UI allows map click to manually set the location and retry.
* **8a — Baseline assessment not found**
  * 8a1: The system applies the configured fallback (e.g., nearest-neighbour baseline or neighbourhood median baseline).
  * 8a2: The UI displays a warning such as “Baseline not available for this parcel; estimate uses fallback.”
* **9a — Some open-data features unavailable**
  * 9a1: The system proceeds with a partial feature set and computes an estimate with reduced confidence.
  * 9a2: The UI shows a non-blocking notice (e.g., “Some datasets unavailable; estimate may be less reliable.”).
* **10a — Valuation engine error**
  * 10a1: The system logs the error with correlation IDs and returns a user-friendly failure message.
  * 10a2: The UI displays “Unable to produce an estimate right now” with a “Try again” action.
* **12a — User changes inputs after seeing the estimate**
  * 12a1: Casey edits an attribute (e.g., `bathrooms` from `2` → `1.5`) and re-submits.
  * 12a2: The UI updates the estimate and clearly indicates that the value is refreshed (new timestamp).

## Data Examples (Illustrative)
Example estimate result for comparison purposes (numbers are illustrative only):
* Input:
  * Address: `10950 97 St NW, Edmonton, AB`
  * Beds/Baths/Size: `3 / 2 / 1500 sq ft`
* Output:
  * Estimated value: `$452,000`
  * Baseline: `$430,000` (Assessment year: `2024`, example)
  * Timestamp: `2026-02-12T18:22:00Z` (example)
  * Warnings: `[]` (or `["Some features missing"]` if applicable)

## Notes / Assumptions
* The “single estimated value” is intended for quick comparison and is not a professional appraisal.
* The UI should present currency formatting and rounding consistently (e.g., nearest `$1,000`), per product requirements.
* The system should always show at least minimal provenance metadata (“as of” timestamp and baseline year/source when available) to support transparency.

