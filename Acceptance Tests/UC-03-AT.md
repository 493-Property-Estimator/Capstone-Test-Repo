# Acceptance Test Suite --- UC-03 (Select Location by Clicking on Map)

## Assumptions (for testability)

-   The system provides an interactive map UI capable of returning click
    coordinates (lat/long or projected coords).
-   Boundary validation can be tested with known in-bound/out-of-bound
    clicks.
-   Coordinate resolution failures can be simulated (map service error,
    projection error, missing tile/click handler failure).
-   Valuation can be mocked to return deterministic values.
-   Missing open-data features can be simulated via mocked services or
    feature flags.

------------------------------------------------------------------------

## AT-01 --- Successful estimate from valid in-bound map click (Happy Path)

**Covers:** Main Success Scenario Steps 1--8

**Given** - The Property Value Estimator system is running - The map UI
is loaded successfully - The click handler is functioning and returns
coordinates - The clicked location is within the supported geographic
boundary - Required valuation data is available

**When** - The user clicks a point on the map within the supported
boundary

**Then** - The system captures the clicked coordinates - The system
confirms the coordinates are within supported boundary - The system
generates a canonical location ID - The system computes an estimate -
The system displays: - a single estimated value - a low/high range - The
estimate is shown at/near the clicked location (e.g., popup) or in a
side panel

**Acceptance Criteria** - Estimate is numeric and non-empty - Low ≤
Estimate ≤ High - The UI clearly associates the estimate with the
clicked point

------------------------------------------------------------------------

## AT-02 --- Click outside supported boundary is rejected

**Covers:** Extension 3a

**Given** - The system is running - The map UI is loaded successfully -
The click handler returns coordinates for the click - The click point is
outside the supported geographic boundary

**When** - The user clicks a point outside the supported boundary

**Then** - The system informs the user the location is outside the
supported area - The system does not compute an estimate - The system
does not display a value/range

**Acceptance Criteria** - User message clearly indicates unsupported
region - No canonical location ID is generated (or it is not used for
valuation)

------------------------------------------------------------------------

## AT-03 --- Coordinate resolution failure shows error and prevents valuation

**Covers:** Extension 4a

**Given** - The system is running - The map UI is loaded - A
map/rendering/projection error occurs such that click coordinates cannot
be resolved

**When** - The user clicks on the map

**Then** - The system displays an error indicating the location could
not be determined - The system does not proceed to boundary validation -
The system does not compute an estimate

**Acceptance Criteria** - Error is user-actionable (e.g., "Try again" /
"Reload map") - No estimate output is shown

------------------------------------------------------------------------

## AT-04 --- Retry after coordinate resolution failure succeeds

**Covers:** Extension 4a2 + return to Main Scenario

**Given** - The system is running - The first click attempt fails to
resolve coordinates - The map recovers and a subsequent click can
resolve coordinates - The second click is in-bound and valuation data is
available

**When** 1. The user clicks and the system fails to resolve coordinates
2. The user clicks again on an in-bound point

**Then** - The first attempt results in an error and no estimate - The
second attempt produces a valid estimate and range

**Acceptance Criteria** - The UI does not remain stuck in an error
state - The second click completes successfully

------------------------------------------------------------------------

## AT-05 --- Partial valuation when some open-data features are unavailable

**Covers:** Extension 7a

**Given** - The system is running - The map UI is loaded and click
coordinates resolve successfully - The clicked location is within
supported boundary - One or more open-data feature sources are
unavailable (simulated) - Baseline assessment data remains available

**When** - The user clicks an in-bound location

**Then** - The system computes a partial estimate using available data -
The system displays estimate and range - The system displays a warning
indicating missing data and reduced accuracy

**Acceptance Criteria** - Estimate and range are still displayed -
Warning is visible and specific (not generic)

------------------------------------------------------------------------

## AT-06 --- Canonical location ID is generated for successful in-bound click

**Covers:** Main Scenario Step 6

**Given** - A click resolves coordinates and is within supported
boundary

**When** - The system processes the click

**Then** - A canonical location ID is generated and used for valuation

**Acceptance Criteria** - Canonical ID is non-empty - Canonical ID is
stable for repeated clicks at the same location (within a tolerance),
assuming no data version change

------------------------------------------------------------------------

## AT-07 --- Rapid repeated clicks update the estimate correctly (UX reliability)

**Given** - The system is running - The map UI is loaded - The user
clicks multiple different in-bound points rapidly

**When** - The user performs 3+ clicks on different in-bound locations
in quick succession

**Then** - The UI updates to show the estimate corresponding to the most
recent click - Prior pending requests do not overwrite the most recent
result

**Acceptance Criteria** - Final displayed estimate matches the last
click location - No mixed or duplicated overlays remain on the UI
(unless intentionally designed)

------------------------------------------------------------------------

## AT-08 --- Estimate invariants are maintained

**Covers:** Output integrity

**Given** - The system computes an estimate for an in-bound click

**When** - The system returns the estimate response

**Then** - Low value ≤ Estimate ≤ High value - All values are numeric
and non-negative - Output formatting is consistent (e.g., currency
formatting if UI)

**Acceptance Criteria** - Output passes validation rules with no
exceptions
