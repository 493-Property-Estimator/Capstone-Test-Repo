# Missing Requirements Review

This project does not fully meet the requirements in `specs/` yet.

This review is based on the current code under `src/backend`, `src/frontend`, `src/data_sourcing`, and `src/estimator`. The list below focuses on high-confidence gaps where the current implementation clearly falls short of the spec behavior.

## 1. Coordinate normalization and coordinate-based estimation are incomplete

**Specs affected**: `002-user-coords`, `004-input-location`, `005-value-location`, `023-property-estimate-api`

**What is missing**

- Raw latitude/longitude requests are validated, but they are not normalized into a canonical location ID.
- There is no parcel/grid fallback normalization flow for valid coordinates.
- A location-only estimate from coordinates alone does not complete successfully unless a canonical property record was already resolved some other way.

**How the current code falls short**

- `src/backend/src/api/estimates.py` only loads baseline data when `canonical_location_id` or `address` resolves to a record.
- If the request contains only `location.coordinates`, `coords` is set, but `canonical` remains `None`, so `baseline_value` stays `None` and the request fails with `BASELINE_MISSING`.
- `src/backend/src/api/locations.py` resolves map clicks by picking the nearest property, but there is no equivalent normalization path for direct coordinate input and no grid-cell fallback.

**Why this matters**

- Spec `002` requires coordinate-based estimation.
- Spec `004` requires all supported input forms to normalize into a stable canonical location ID, including fallback spatial units.
- Spec `005` requires location-only estimation from address, coordinates, or map click.

**Code evidence**

- `src/backend/src/api/estimates.py:36-47`
- `src/backend/src/api/estimates.py:83-97`
- `src/backend/src/api/locations.py:45-81`

## 2. Property details are collected in the UI but ignored by the backend

**Specs affected**: `006-property-details-estimate`, `013-single-value-estimate`

**What is missing**

- Bedrooms, bathrooms, and floor area are never used to refine the estimate.
- There is no backend validation for positive/non-negative property detail rules.
- There is no response indicator showing whether attributes were incorporated fully or partially.

**How the current code falls short**

- The frontend sends `property_details` in the estimate payload.
- The backend estimate endpoint never reads `payload["property_details"]`.
- The estimate range is fixed at `±7%`, so attribute-based estimates cannot narrow the range as the spec requires.

**Why this matters**

- Spec `006` requires valid property details to refine estimates and produce a narrower or more precise result.
- Spec `013` expects optional attributes to be accepted and preserved meaningfully in the estimate flow.

**Code evidence**

- `src/frontend/src/features/estimate/estimateController.js:72-88`
- `src/backend/src/api/estimates.py:27-30`
- `src/backend/src/api/estimates.py:132-158`

## 3. Estimator feature coverage is much narrower than the spec set

**Specs affected**: `007-amenity-proximity`, `008-travel-accessibility`, `009-green-space-coverage`, `010-school-distance-signals`, `011-commute-accessibility`, `012-neighbourhood-indicators`, `015-top-contributing-factors`, `016-assessment-baseline`

**What is missing**

- No amenity desirability aggregates or configurable weighting.
- No travel-time or destination-set accessibility computation.
- No green-space area or coverage calculation.
- No school suitability metrics beyond nearest-school distance.
- No employment-center commute accessibility computation.
- No neighbourhood indicators or composite local profile.
- No true top positive/top negative factor ranking in the API response.
- No richer baseline provenance/fallback policy beyond direct assessment lookup.

**How the current code falls short**

- `compute_proximity_factors` only computes four simple nearest-feature adjustments: school, park, police proxy, and playground.
- Commute/routing fallback is simulated, but not tied to actual destinations or factor calculations.
- The API response exposes a flat `factor_breakdown`, but not explicit top positive and top negative factors.
- Baseline handling is a single record lookup; there is no broader baseline selection logic or baseline metadata in the active API.

**Why this matters**

- Specs `007` through `012` describe separate feature families with their own metrics, fallback behavior, and deterministic outputs.
- Spec `015` requires ranked contributing factors.
- Spec `016` requires an assessment-baseline workflow richer than a single direct value lookup.

**Code evidence**

- `src/backend/src/services/features.py:28-140`
- `src/backend/src/services/routing.py:29-46`
- `src/backend/src/api/estimates.py:99-173`

## 4. Estimate output and warning behavior is only partial

**Specs affected**: `013-single-value-estimate`, `014-low-high-range`, `026-missing-data-warnings`, `028-partial-open-data-results`

**What is missing**

- No estimate timestamp in the active API response.
- Range generation is static and not driven by data quality, attributes, or factor confidence.
- Missing-data warnings are generic and do not explain per-factor impact in detail.
- The system hard-fails when the baseline is missing instead of supporting a lower-confidence partial estimate where policy allows.

**How the current code falls short**

- The active API returns `final_estimate`, `range`, `confidence`, and `warnings`, but no timestamp.
- Warning generation collapses all missing factors into one generic message.
- The frontend warning UI can collapse/reopen warnings, but it does not provide factor-specific explanation or tooltip-style impact detail.

**Why this matters**

- Specs `013` and `014` require more deliberate result packaging and range behavior.
- Spec `026` expects specific missing-data guidance and stronger degraded/fallback messaging.
- Spec `028` expects partial results with reliability signaling, not only hard failure, for more cases.

**Code evidence**

- `src/backend/src/api/estimates.py:87-97`
- `src/backend/src/api/estimates.py:134-172`
- `src/backend/src/services/warnings.py:6-25`
- `src/frontend/src/features/warnings/warningController.js:6-72`

## 5. API contract and invalid-input handling do not fully meet the specs

**Specs affected**: `023-property-estimate-api`, `032-invalid-input-errors`

**What is missing**

- No authentication or authorization on the estimate endpoint.
- No request time-budget handling.
- No specialized polygon validation beyond a generic unsupported error.
- No corrective guidance for syntactically valid but unresolvable addresses beyond a generic resolution failure.
- No property-reference types beyond address, coordinates, and canonical ID.

**How the current code falls short**

- The estimate route is open and does not check credentials.
- Validation supports only simple address/coordinate checks and a generic unsupported polygon issue.
- An unresolvable address becomes `UNRESOLVABLE_LOCATION`, but the response does not guide the caller toward postal code or coordinate fallback as required by the spec.

**Why this matters**

- Spec `023` explicitly includes authenticated access and controlled failures for unsupported or invalid requests.
- Spec `032` expects structured, actionable error guidance for invalid and specialized inputs.

**Code evidence**

- `src/backend/src/api/estimates.py:18-25`
- `src/backend/src/api/estimates.py:48-58`
- `src/backend/src/services/validation.py:45-91`
- `src/backend/src/services/errors.py:6-30`

## 6. Search and map UI flows are only partially aligned with the specs

**Specs affected**: `001-user-geocode`, `003-user-map`, `024-address-map-search`, `025-open-data-layers`

**What is missing**

- Ambiguous-address candidate selection stores a synthetic candidate ID instead of the real canonical location ID.
- The map adapter contains an extra root click handler that references `bounds` outside scope.
- Layer loading is debounced, but there is no progressive rendering/loading progress behavior for heavy datasets.
- Partial layer coverage is returned by the API, but the UI does not surface that as a clear warning state.

**How the current code falls short**

- Search candidates are returned with `candidate_id = "cand_<canonical_id>"`, and the frontend stores that as `canonical_location_id`.
- The duplicate click handler can throw a runtime error or create inconsistent click behavior.
- The layers UI mainly shows ready/unavailable state and map chips, not the fuller heavy-data UX described by the specs.

**Why this matters**

- Specs `001`, `003`, and `024` depend on stable location resolution and retryable UI flows.
- Spec `025` expects richer layer-state handling than the current implementation provides.

**Code evidence**

- `src/backend/src/api/search.py:60-75`
- `src/frontend/src/features/search/searchController.js:121-129`
- `src/frontend/src/map/mapAdapter.js:204-215`
- `src/backend/src/api/layers.py:52-60`
- `src/frontend/src/features/layers/layerController.js:57-82`

## 7. Routing fallback and cache behavior are only partially implemented

**Specs affected**: `027-straight-line-fallback`, `029-cache-computations`, `031-health-service-metrics`

**What is missing**

- There is no actual road-routing success path in the active backend.
- Mixed-mode routing behavior is not implemented.
- Cache signatures are not normalized for semantically equivalent requests.
- Cache corruption/unavailability handling is not implemented.
- Health and metrics coverage is smaller than the monitoring spec requires.

**How the current code falls short**

- `compute_distance` always returns straight-line distance, whether routing is enabled or not.
- The estimate path calls routing with the same origin and target coordinates, so it does not compute useful accessibility distances.
- Cache keys use raw lat/lng/address string values, which means formatting differences can produce different keys.
- Health only checks feature-store connectivity, cache presence, routing provider status, and dataset version existence. It does not check memory/thread pool/valuation engine or rate-limit health polling.

**Why this matters**

- Spec `027` expects routing to work normally when healthy and fall back only on failure.
- Spec `029` expects canonical cache signatures and safe degradation when cache issues occur.
- Spec `031` expects broader monitoring and endpoint hardening.

**Code evidence**

- `src/backend/src/services/routing.py:29-46`
- `src/backend/src/api/estimates.py:104-114`
- `src/backend/src/api/estimates.py:182-190`
- `src/backend/src/api/health.py:14-67`

## 8. Scheduled refresh and grid precomputation are only partially implemented

**Specs affected**: `022-schedule-refresh-jobs`, `030-precompute-grid-features`

**What is missing**

- No actual scheduler is present; only a callable workflow exists.
- Refresh runs track step order and retries, but there is no active-run monitoring surface in the app.
- Grid precomputation only stores property count plus mean/median baseline value.
- Grid feature persistence does not include dataset versions, broader aggregate families, quarantine behavior, or write rollback/retry handling.

**How the current code falls short**

- The refresh workflow can be invoked manually or with a `scheduled` trigger value, but nothing in the project schedules it automatically.
- The precompute job recreates a single `grid_features_prod` table with a very small schema and deletes/rebuilds it in one pass.

**Why this matters**

- Spec `022` is about a real refresh-job orchestration capability, not only a callable workflow function.
- Spec `030` requires far more than simple mean/median property aggregation.

**Code evidence**

- `src/data_sourcing/workflow.py:31-213`
- `src/backend/src/jobs/precompute_grid.py:14-93`

## Notes

- I did not flag specs `017-geospatial-ingest`, `018-census-ingest`, `019-ingest-tax-assessments`, `020-standardize-poi-categories`, or `021-deduplicate-open-data` in this file because the repository does contain dedicated pipeline implementations for those areas. That is not the same as proving they are fully complete; it only means I did not find a clear, high-confidence mismatch quickly enough to include them here.
- The active backend and frontend already implement meaningful portions of the spec set, but they do not fully satisfy the folder as a whole in their current state.
