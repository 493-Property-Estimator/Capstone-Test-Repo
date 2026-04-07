# Use Case Implementation Matrix

## Purpose

This matrix is intended to drive the final implementation phase under a flow-based marking scheme. Each use case is classified according to the current repository state as one of:

- `Satisfied`: implemented with credible runtime and test evidence for the main intended flow
- `Partial`: core pieces exist, but one or more important flows, datasets, or acceptance expectations are incomplete
- `Not Evidenced`: insufficient implementation or verification evidence in the current codebase

## Matrix

| UC | User Story Summary | Status | Main Reason |
|---|---|---|---|
| UC-01 | Estimate by address | Satisfied | Address search, resolution, estimate request, and UI flow are implemented and tested. |
| UC-02 | Estimate by lat/long | Satisfied | Coordinate-driven estimate flow is implemented and tested. |
| UC-03 | Estimate by map click | Satisfied | Map click selection, drag guard, and estimate flow exist and are tested. |
| UC-04 | Normalize to canonical location | Satisfied | Backend normalization and location resolution endpoints are present. |
| UC-05 | Estimate using location only | Satisfied | Minimal-input estimate path is supported. |
| UC-06 | Provide basic property details | Satisfied | Beds, baths, and area are accepted and used in estimates. |
| UC-07 | Proximity to amenities | Partial | Amenities are used, but full acceptance evidence across all configured amenity categories is incomplete. |
| UC-08 | Travel-based distance for accessibility | Partial | Routing fallback behavior exists, but real travel-path support is still limited. |
| UC-09 | Green space coverage | Partial | Green-space-related factors exist, but full green-space coverage expectations are not clearly proven end to end. |
| UC-10 | Distance to schools | Partial | School signals exist, but full acceptance coverage is not clearly demonstrated. |
| UC-11 | Distance to employment centers / commute | Partial | Current estimator uses a downtown proxy rather than full employment-center targeting. |
| UC-12 | Neighbourhood indicators | Partial | Indicators degrade when census data is unavailable; full happy-path coverage is not assured. |
| UC-13 | Return a single estimated value | Satisfied | Point estimate is returned and rendered. |
| UC-14 | Return a low/high range | Satisfied | Estimate range is returned and rendered. |
| UC-15 | Show top contributing factors | Satisfied | Factor breakdown and top-factor UI are implemented. |
| UC-16 | Use assessment baseline | Satisfied | Baseline metadata and estimate anchoring are implemented. |
| UC-17 | Ingest open geospatial datasets | Partial | Pipelines exist, but full end-to-end evidence across expected datasets is incomplete. |
| UC-18 | Ingest municipal census datasets | Partial | Census ingestion exists in code, but current runtime evidence is incomplete and census-backed UI behavior is not guaranteed. |
| UC-19 | Ingest property tax assessment data | Partial | Assessment ingestion is central and working, but not all acceptance flows are explicitly evidenced. |
| UC-20 | Standardize POI categories | Partial | Standardization logic exists, but full acceptance verification is not yet demonstrated. |
| UC-21 | Deduplicate open-data entities | Partial | Deduplication exists, but complete acceptance-level verification is not evident. |
| UC-22 | Schedule open-data refresh jobs | Partial | Scheduler and refresh routes exist, but full operational acceptance evidence is incomplete. |
| UC-23 | Provide estimate API endpoint | Satisfied | Endpoint exists, validates inputs, and serves the frontend. |
| UC-24 | Search by address in map UI | Satisfied | Search UI and backend integration are implemented and tested. |
| UC-25 | Toggle open-data layers in map UI | Partial | Layer toggling works, but the main UI layer set is narrower than the documented acceptance assumptions. |
| UC-26 | Show missing-data warnings in UI | Satisfied | Missing-data warnings and degraded-result messaging are implemented. |
| UC-27 | Fall back to straight-line distance when routing fails | Satisfied | Fallback logic and warnings are implemented. |
| UC-28 | Provide partial results when data is unavailable | Satisfied | Partial responses and warnings are implemented. |
| UC-29 | Cache frequently requested computations | Satisfied | Backend and viewport caching paths exist. |
| UC-30 | Precompute grid-level features | Partial | Endpoint/job exists, but full acceptance-grade proof is incomplete. |
| UC-31 | Provide health checks and service metrics | Satisfied | Health and metrics endpoints exist. |
| UC-32 | Provide clear error messages for invalid inputs | Satisfied | Structured validation and frontend error handling exist. |

## Highest-Priority Gaps To Close

### 1. UC-11

Replace the downtown-only commute proxy with employment-center-based commute computation that matches the use case and acceptance tests.

### 2. UC-12

Ensure `census_prod` is populated and wired so neighbourhood indicators satisfy the full happy path rather than only degraded behavior.

### 3. UC-25

Align the main UI layer set with the accepted requirement set, or explicitly reconcile the requirement documents if the intended layer scope has changed.

### 4. UC-17 through UC-22 and UC-30

Run and document end-to-end ingestion, scheduler, and precompute flows with deterministic evidence instead of relying on code presence alone.

## Recommended Working Method

For each `Partial` item:

1. read the corresponding use case
2. read the scenario
3. read the acceptance test
4. implement exactly the missing flow(s)
5. run the flow manually
6. record pass/fail evidence

This matrix should be updated as those gaps are closed.
