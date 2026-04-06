# Missing Requirements Review (V2)

This file lists requirements that are **still missing** in the current `src` implementation after re-checking `src/` against `specs/` and comparing with `Missing.md`.

## 1) Canonical location normalization is still incomplete

**Specs affected**: `001-user-geocode`, `002-user-coords`, `003-user-map`, `004-input-location`, `024-address-map-search`

- Coordinate-only estimate requests can succeed, but there is still no explicit backend normalization flow that always produces a stable canonical ID (with parcel/grid fallback semantics from spec `004`).
- Ambiguous search candidate selection still stores a synthetic ID (`cand_<canonical_id>`) as `canonical_location_id` in the frontend.

**Code evidence**
- `src/backend/src/api/estimates.py` (no dedicated coordinate->canonical normalization step before estimation)
- `src/backend/src/api/search.py` (`candidate_id` generated as `cand_<id>`)
- `src/frontend/src/features/search/searchController.js` (writes `candidate.candidate_id` into `canonical_location_id`)

## 2) Property-details support is partial, not fully spec-compliant

**Specs affected**: `006-property-details-estimate`, `013-single-value-estimate`

- Backend does not validate non-negative bedrooms/bathrooms (or other attribute constraints) before computing.
- `floor_area_sqft` sent by frontend is not mapped to estimator keys (`total_gross_area`), so floor-area refinement is effectively missing.
- Response does not explicitly indicate which user-provided attributes were incorporated (full vs partial incorporation signal).

**Code evidence**
- `src/backend/src/api/estimates.py` (passes `property_details` through with no attribute validation)
- `src/backend/src/services/validation.py` (location validation only)
- `src/frontend/src/features/estimate/estimateController.js` (`floor_area_sqft` payload field)
- `src/estimator/property_estimator.py` (`_normalize_attributes` expects `total_gross_area`)

## 3) Estimate API contract gaps remain (auth, input types, guidance)

**Specs affected**: `023-property-estimate-api`, `032-invalid-input-errors`

- No authentication/authorization checks on `/api/v1/estimates`.
- Property reference support is limited; polygon and property-ID based estimation paths are not implemented as required.
- Polygon errors are generic "unsupported" responses rather than specialized geometry validation guidance.
- Unresolvable location handling lacks richer corrective guidance/disambiguation behavior expected by spec-level contract.

**Code evidence**
- `src/backend/src/app.py` (estimate router added with no auth dependency)
- `src/backend/src/services/validation.py` (`location.polygon` always unsupported)
- `src/backend/src/api/estimates.py` (only canonical ID/address/coordinates path)

## 4) Cache requirements are still largely unimplemented in the active estimate path

**Specs affected**: `023-property-estimate-api`, `029-cache-computations`

- In-memory cache exists but is not wired into `/api/v1/estimates` request handling.
- No canonical request-signature normalization, no cache lookup/set lifecycle in endpoint, and no cache status signaling on responses.
- No explicit corrupted-cache handling path in the estimate endpoint.

**Code evidence**
- `src/backend/src/app.py` (creates `MemoryCache`)
- `src/backend/src/api/estimates.py` (no cache usage)
- `src/backend/src/services/cache.py` (utility exists but not integrated)

## 5) Time-budget timeout behavior is missing

**Specs affected**: `023-property-estimate-api`

- No configured valuation time budget enforcement and no controlled `503` timeout path when compute exceeds budget.

**Code evidence**
- `src/backend/src/api/estimates.py` (no timeout wrapper / deadline logic)
- `src/backend/src/config.py` (no estimate time-budget setting)

## 6) Response contract still misses required output fields

**Specs affected**: `013-single-value-estimate`, `015-top-contributing-factors`, `016-assessment-baseline`

- No estimate production timestamp in success response.
- Baseline metadata from estimator (baseline type/source/year/distance) is not surfaced by API response; only `baseline_value` is returned.
- Estimator computes `top_positive_factors` and `top_negative_factors`, but API adapter drops them.

**Code evidence**
- `src/backend/src/api/estimates.py` (`_adapt_estimator_response` omits timestamp, top factors, baseline metadata)
- `src/estimator/property_estimator.py` (produces baseline object and top factor lists)

## 7) Missing-data explainability is reduced at API adaptation layer

**Specs affected**: `015-top-contributing-factors`, `026-missing-data-warnings`, `028-partial-open-data-results`

- Warning adaptation clears `affected_factors` to `[]`, discarding factor-level warning linkage from estimator warnings.
- Factor adaptation marks all returned factors as `status: "available"`; missing categories are not represented in the breakdown as required for partial-result explainability.

**Code evidence**
- `src/backend/src/api/estimates.py` (`_adapt_warning`, `_adapt_factor`)

## 8) Some feature families from 007-012 are still not implemented end-to-end

**Specs affected**: `007-amenity-proximity`, `008-travel-accessibility`, `009-green-space-coverage`, `010-school-distance-signals`, `011-commute-accessibility`, `012-neighbourhood-indicators`

- Current estimator has meaningful proximity/context logic, but still lacks several spec-defined families (for example explicit green-space coverage metrics, employment-center commute accessibility outputs, and richer school suitability signal set).
- Factor outputs are present, but not all required metric families and representations are exposed through the active API contract.

**Code evidence**
- `src/estimator/property_estimator.py` (implemented factor set)
- `src/backend/src/api/estimates.py` (exposed subset via adapted response)

## 9) Scheduler and refresh observability are still partial

**Specs affected**: `022-schedule-refresh-jobs`

- Refresh workflow exists, but there is no actual in-app scheduler/orchestrator process that triggers it automatically.
- No dedicated API surface for active run monitoring/status polling in the main backend app.

**Code evidence**
- `src/data_sourcing/workflow.py` (callable workflow only)
- `src/data_sourcing/cli.py` (manual/CLI trigger)

## 10) Grid precompute remains minimal versus spec scope

**Specs affected**: `030-precompute-grid-features`

- Grid precompute currently stores only property count + mean/median baseline values.
- Missing broader per-cell aggregate families (amenities, green-space density, crime indices, etc.), richer validation/quarantine behavior, and retry/rollback semantics expected by spec.

**Code evidence**
- `src/backend/src/jobs/precompute_grid.py`

## 11) Health endpoint is still narrower than monitoring spec

**Specs affected**: `031-health-service-metrics`

- Health checks do not include thread pool/memory/process health checks.
- No health endpoint rate limiting for excessive polling.
- Dependency coverage is limited relative to spec (valuation-engine/open-data-source detail is not comprehensively reported).

**Code evidence**
- `src/backend/src/api/health.py`
