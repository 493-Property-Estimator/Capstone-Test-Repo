# Missing Functionality Report

## Scope

This report compares the current application against the repository's requirement sources:

- [`Property_Value_Estimator_User_Stories_Updated.md`](/root/Speckit-Constitution-To-Tasks/Property_Value_Estimator_User_Stories_Updated.md)
- [`Use Cases/`](/root/Speckit-Constitution-To-Tasks/Use%20Cases)
- [`Scenarios/`](/root/Speckit-Constitution-To-Tasks/Scenarios)
- [`Acceptance Tests/`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests)
- implementation in [`src/frontend/`](/root/Speckit-Constitution-To-Tasks/src/frontend), [`src/backend/`](/root/Speckit-Constitution-To-Tasks/src/backend), [`src/estimator/`](/root/Speckit-Constitution-To-Tasks/src/estimator), and [`src/data_sourcing/`](/root/Speckit-Constitution-To-Tasks/src/data_sourcing)

The goal is not to restate what exists, but to identify where the current version is still partial or not evidenced against the stated requirements.

## Overall Assessment

The current application satisfies the main user-facing core flow:

- search by address
- select by coordinates
- select by map click
- view clustered assessment properties
- inspect property details
- request an estimate
- receive warnings and partial-result messaging
- toggle the currently exposed map layers

However, the application does **not** satisfy all requirements across all 32 user stories and acceptance suites. The current state is best described as:

- core application flow: implemented
- frontend-owned acceptance slice: largely satisfied
- full backlog and full acceptance corpus: partially satisfied

## Status Summary

### Satisfied or Mostly Satisfied

- `UC-01` Enter Street Address to Estimate Property Value
- `UC-02` Enter Latitude/Longitude to Estimate Property Value
- `UC-03` Select Location by Clicking on Map
- `UC-04` Normalize to Canonical Location
- `UC-05` Estimate Using Location Only
- `UC-06` Provide Basic Property Details
- `UC-13` Return a Single Estimated Value
- `UC-14` Return a Low/High Range
- `UC-15` Show Top Contributing Factors
- `UC-16` Use Assessment Baseline
- `UC-23` Provide Estimate API Endpoint
- `UC-24` Search by Address in the Map UI
- `UC-26` Show Missing-Data Warnings in UI
- `UC-27` Fall Back to Straight-Line Distance When Routing Fails
- `UC-28` Provide Partial Results When Some Open Data Is Unavailable
- `UC-29` Cache Frequently Requested Computations
- `UC-31` Provide Health Checks and Service Metrics
- `UC-32` Provide Clear Error Messages for Invalid Inputs

### Partially Satisfied

- `UC-07` Proximity to Amenities
- `UC-08` Travel-Based Distance for Accessibility
- `UC-09` Green Space Coverage
- `UC-10` Distance to Schools
- `UC-11` Commute Accessibility / Employment Centers
- `UC-12` Neighbourhood Indicators
- `UC-17` Ingest Open Geospatial Datasets
- `UC-18` Ingest Municipal Census Datasets
- `UC-19` Ingest Property Tax Assessment Data
- `UC-20` Standardize POI Categories Across Sources
- `UC-21` Deduplicate Open-Data Entities
- `UC-22` Schedule Open-Data Refresh Jobs
- `UC-25` Toggle Open-Data Layers in the Map UI
- `UC-30` Precompute Grid-Level Features

### Not Evidenced as Fully Satisfied

- Full end-to-end acceptance conformance for every suite in [`Acceptance Tests/`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests)
- Full happy-path availability of all optional datasets assumed by the specs

## Main Requirement Gaps

### 1. Commute Accessibility Is a Downtown Proxy, Not Full Employment-Center Support

`UC-11` requires travel-based accessibility to employment centers, including identification of relevant commute targets, routing or fallback distance computation, and aggregated commute indicators. The current implementation does not appear to do that fully.

[`Use Cases/UC-11.md`](/root/Speckit-Constitution-To-Tasks/Use%20Cases/UC-11.md) expects employment centers and aggregate commute metrics. In contrast, the current implementation uses a single downtown point. [`src/estimator/proximity.py`](/root/Speckit-Constitution-To-Tasks/src/estimator/proximity.py#L211) implements `get_downtown_accessibility(...)`, and [`src/estimator/property_estimator.py`](/root/Speckit-Constitution-To-Tasks/src/estimator/property_estimator.py#L328) builds commute context around `DOWNTOWN_EDMONTON`.

This means the application currently provides a commute-style signal, but not the full employment-center-based behavior required by `UC-11` and its acceptance tests.

### 2. Census-Based Neighbourhood Indicators Are Conditional and Can Be Omitted

`UC-12` expects neighbourhood indicators and a summarized context profile. The current estimator explicitly omits census-derived indicators if the `census_prod` table is empty or unavailable.

[`src/estimator/property_estimator.py`](/root/Speckit-Constitution-To-Tasks/src/estimator/property_estimator.py#L411) checks whether `census_prod` has rows and emits warnings when it does not. That is a reasonable degradation path, but it does not satisfy the full happy path described in [`Acceptance Tests/UC-12-AT.md`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests/UC-12-AT.md), which expects configured indicators to be present.

So `UC-12` is supported in degraded form, not proven complete in all required modes.

### 3. Open-Data Layer UI Does Not Fully Match the Acceptance Scope

The map layer feature works, but the currently exposed main-page layer set is narrower than the acceptance suite suggests.

[`Acceptance Tests/UC-25-AT.md`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests/UC-25-AT.md) assumes layer controls for Schools, Parks, Census, and Assessment Zones. The main app currently limits the main-page layer controls to:

- `schools`
- `parks`
- `playgrounds`
- `transit_stops`

This is hardcoded in [`src/frontend/src/features/layers/layerController.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/features/layers/layerController.js#L15).

The configuration still knows about additional layers in [`src/frontend/src/config.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/config.js#L158), but not all of them are surfaced in the main app. Therefore, `UC-25` is implemented, but not fully aligned with the documented acceptance assumptions.

### 4. Crime Data Exists, But Not as a Rich Granular Map Dataset

The codebase includes crime support and warnings for unavailable crime context. The current data model uses `crime_summary_prod`, which is useful for neighbourhood-level or summary scoring, but it is not equivalent to a rich point-level crime incident layer.

This matters because some requirements imply richer local-context usage than a simple summary table can provide. The current implementation supports crime-aware degradation and some contextual features, but it does not demonstrate full spatial richness for crime-related use cases.

### 5. Full Ingestion/Scheduler/Refresh Backlog Is Present but Not Fully Proven End-to-End

The repository contains ingestion pipelines and scheduler support, and many of the backend/data features are present in code. However, there is not enough evidence in the current app state to claim every ingestion and scheduling acceptance suite is fully satisfied in production-like execution against all intended datasets.

This affects:

- `UC-17`
- `UC-18`
- `UC-19`
- `UC-20`
- `UC-21`
- `UC-22`
- `UC-30`

These features are partly implemented and partly evidenced, but not fully proven complete just from the current runtime and frontend behavior.

## Frontend-Specific Notes

The frontend-owned scope is in much better shape than the full backlog. The frontend test traceability file [`src/frontend/tests/README.md`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/README.md#L5) explicitly maps tests to:

- `UC-01`
- `UC-02`
- `UC-03`
- `UC-24`
- `UC-25`
- `UC-26`
- `UC-32`

That indicates the frontend-owned acceptance slice is actively maintained and tested. The main remaining frontend inadequacy is not that the current UI is broken, but that the layer scope in the main app is narrower than the broader map-layer acceptance assumptions.

## Practical Conclusion

The current version of the application should not be described as satisfying **all** requirements in the user stories, specifications, scenarios, and acceptance tests.

A more accurate statement is:

The application satisfies the core end-user product flow and much of the frontend-owned scope, while several data, valuation, commute, neighbourhood-context, and broader acceptance-suite requirements remain only partially satisfied or not fully evidenced.

## Recommended Next Steps

1. Bring `UC-11` to spec by implementing real employment-center targeting rather than a downtown-only proxy.
2. Verify or populate `census_prod` so `UC-12` can satisfy full neighbourhood-indicator expectations.
3. Decide whether the main app should expose the broader `UC-25` layer set or whether the acceptance scope needs to be narrowed.
4. Audit the ingestion and scheduler stories (`UC-17` through `UC-22`, `UC-30`) with explicit end-to-end test evidence.
5. Produce a full compliance matrix mapping `UC-01` through `UC-32` to `satisfied`, `partial`, or `not evidenced`.
