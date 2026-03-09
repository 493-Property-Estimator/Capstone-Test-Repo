# Property Value Estimator — Edmonton Open-Data User Stories

## Epic 1 — Property Input & Normalization

### ### US-1: Estimate by address
**Priority:** Must
As a general user; I want to enter a street address; so that I can estimate value without coordinates.

### ### US-2: Estimate by lat/long
**Priority:** Must
As a general user; I want to input latitude/longitude; so that I can estimate value when no address exists.

### ### US-3: Estimate by map click
**Priority:** Should
As a general user; I want to click on the map; so that I can quickly evaluate locations.

### ### US-4: Normalize inputs to a canonical location
**Priority:** Must
As a backend system; I want to normalize property inputs to a canonical location ID; so that downstream features are consistent.

### ### US-5: Support minimal input (location-only)
**Priority:** Must
As a general user; I want to get an estimate from location alone; so that I can still receive a result with limited details.

### ### US-6: Support standard input (location + basic attributes)
**Priority:** Should
As a general user; I want to provide basic property details (size, beds, baths); so that I can get a more accurate estimate.



## Epic 2 — Open-Data Feature Computation

### ### US-7: Consider proximity to amenities
**Priority:** Must
As a valuation engine; I want proximity to amenities (schools, parks, hospitals); so that I can derive baseline desirability.

### ### US-8: Consider travel distance when available
**Priority:** Should
As a valuation engine; I want travel distance; so that accessibility reflects real travel paths.

### ### US-9: Provide green space coverage
**Priority:** Should
As a user; I want green space coverage; so that I can evaluate environmental desirability.

### ### US-10: Consider distance to schools
**Priority:** Should
As a user; I want distance-to-school signals; so that I can evaluate family suitability.

### ### US-11: Consider distance to employment centers
**Priority:** Could
As a user; I want commute accessibility; so that I can gauge work access.

### ### US-12: Provide neighbourhood indicators
**Priority:** Should
As a user; I want neighbourhood indicators; so that I can understand local context.



## Epic 3 — Valuation Output & Explainability

### ### US-13: Return a single estimated value
**Priority:** Must
As a user; I want a single estimated value; so that I can quickly interpret the result.

### ### US-14: Return a low/high range
**Priority:** Must
As a user; I want an estimate range; so that I can understand uncertainty.

### ### US-15: Show top contributing factors
**Priority:** Must
As a user; I want to see key drivers; so that I can understand why the value changed.

### ### US-16: Use assessment baseline
**Priority:** Must
As a user; I want the estimate anchored to the assessment baseline; so that adjustments are explainable.



## Epic 4 — Data Ingestion & Governance (Open Data Only)

### ### US-17: Ingest open geospatial datasets
**Priority:** Must
As a maintainer; I want to ingest open roads, boundaries, and POIs; so that baseline spatial context exists.

### ### US-18: Ingest municipal census datasets
**Priority:** Should
As a maintainer; I want to ingest municipal census data; so that neighbourhood indicators can be computed.

### ### US-19: Ingest property tax assessment data
**Priority:** Must
As a maintainer; I want to ingest property tax assessment data; so that baseline values are available for estimation.

### ### US-20: Standardize POI categories across sources
**Priority:** Must
As a maintainer; I want standardized POI categories; so that features are consistent across open sources.

### ### US-21: Deduplicate open-data entities
**Priority:** Should
As a maintainer; I want deduplication; so that entities are not double-counted.

### ### US-22: Schedule open-data refresh jobs
**Priority:** Must
As a maintainer; I want scheduled refresh cycles; so that data stays current.

## Epic 5 — API & UX

### ### US-23: Provide an estimate API endpoint
**Priority:** Must
As a developer; I want an estimate API; so that I can integrate valuation into other apps.

### ### US-24: Search by address in the map UI
**Priority:** Must
As a general user; I want address search; so that I can navigate quickly.

### ### US-25: Toggle open-data layers in the map UI
**Priority:** Should
As a general user; I want to toggle layers (schools, parks, census boundaries, assessment zones); so that I can explore impacts visually.

### ### US-26: Show missing-data warnings in UI
**Priority:** Should
As a user; I want missing-data warnings; so that I don’t over-trust results.



## Epic 6 — Resilience & Fallbacks

### ### US-27: Fall back to straight-line distance when routing fails
**Priority:** Must
As a valuation engine; I want a routing fallback; so that estimates still work when routing data is down.

### ### US-28: Provide partial results when some open data is unavailable
**Priority:** Must
As a user; I want partial results; so that I can still get a usable estimate.



## Epic 7 — Performance & Reliability

### ### US-29: Cache frequently requested computations
**Priority:** Must
As a backend system; I want caching for repeated requests; so that I reduce cost and latency.

### ### US-30: Precompute grid-level features
**Priority:** Should
As a maintainer; I want precomputed region/grid features; so that estimates can be served faster.

### ### US-31: Provide health checks and service metrics
**Priority:** Must
As a maintainer; I want health checks and metrics; so that I can monitor uptime and performance.



## Epic 8 — Developer Experience

### ### US-32: Provide clear error messages for invalid inputs
**Priority:** Must
As a developer; I want actionable validation errors; so that I can fix requests quickly.
