# Acceptance Test Suite --- UC-02 (Enter Latitude/Longitude)

## Assumptions (for testability)

-   The system exposes an estimate UI or API that accepts
    latitude/longitude.
-   Spatial boundary validation can be tested (e.g., by using known
    in-bound and out-of-bound coordinates).
-   The valuation engine can be mocked to return deterministic results.
-   Missing open-data features can be simulated via feature flags or
    mocked services.

------------------------------------------------------------------------

## AT-01 --- Successful estimate by valid latitude/longitude (Happy Path)

**Covers:** Main Success Scenario Steps 1--8

**Given** - The Property Value Estimator system is running - Required
spatial datasets for normalization and valuation are available - The
coordinates are within the supported geographic boundary - Required
valuation data is available

**When** - The user submits valid numeric latitude/longitude within
valid ranges

**Then** - The system validates coordinate ranges successfully - The
system confirms the coordinates are within the supported boundary - The
system generates a canonical location ID - The system computes an
estimate - The system displays: - a single estimated value - a low/high
range - The request completes without errors

**Acceptance Criteria** - Estimate is numeric and non-empty - Low ≤
Estimate ≤ High - Response time meets SLA (if defined)

------------------------------------------------------------------------

## AT-02 --- Latitude out of range is rejected (Invalid/Out-of-Range)

**Covers:** Extension 4a

**Given** - The system is running

**When** - The user submits latitude \< −90 or \> +90 (with any
longitude)

**Then** - The system rejects the request with a validation error - The
system does not proceed to boundary validation or valuation - No
estimate is shown

**Acceptance Criteria** - Error message references acceptable latitude
range - No valuation computation occurs

------------------------------------------------------------------------

## AT-03 --- Longitude out of range is rejected (Invalid/Out-of-Range)

**Covers:** Extension 4a

**Given** - The system is running

**When** - The user submits longitude \< −180 or \> +180 (with any
latitude)

**Then** - The system rejects the request with a validation error - The
system does not proceed to boundary validation or valuation - No
estimate is shown

**Acceptance Criteria** - Error message references acceptable longitude
range - No valuation computation occurs

------------------------------------------------------------------------

## AT-04 --- Non-numeric coordinate input is rejected

**Covers:** Extension 4a (syntactically invalid)

**Given** - The system is running

**When** - The user submits latitude/longitude where one or both values
are not numeric (e.g., "abc", empty string)

**Then** - The system rejects the request with a validation error - The
system does not proceed to boundary validation or valuation - No
estimate is shown

**Acceptance Criteria** - Error message indicates numeric format is
required

------------------------------------------------------------------------

## AT-05 --- User corrects invalid coordinates and succeeds

**Covers:** Extension 4a2 + return to Main Scenario

**Given** - The system is running - The corrected coordinates are within
supported boundary - Valuation data is available

**When** 1. The user submits invalid coordinates 2. The system shows a
validation error 3. The user corrects the coordinates and resubmits

**Then** - The system accepts corrected input - The system produces and
displays estimate and range

**Acceptance Criteria** - No estimate shown on first invalid attempt -
Estimate and range shown on corrected attempt

------------------------------------------------------------------------

## AT-06 --- Coordinates outside supported boundary are rejected

**Covers:** Extension 5a

**Given** - The system is running - The submitted coordinates are valid
numeric values within global ranges - The submitted coordinates fall
outside the supported geographic boundary

**When** - The user submits out-of-bound coordinates

**Then** - The system reports the location is outside the supported
area - The system does not generate a canonical location ID - The system
does not compute an estimate

**Acceptance Criteria** - No estimate displayed - Message clearly
indicates unsupported geographic area

------------------------------------------------------------------------

## AT-07 --- Valuation proceeds with partial open-data unavailable

**Covers:** Extension 7a

**Given** - The system is running - Coordinates are valid and inside
supported boundary - One or more feature datasets are unavailable
(simulated) - Baseline assessment data remains available

**When** - The user submits valid in-bound coordinates

**Then** - The system produces a partial estimate - The system displays
estimate and range - The system displays a missing-data warning
indicating reduced accuracy

**Acceptance Criteria** - Estimate and range are present despite missing
data - Warning is visible and specific

------------------------------------------------------------------------

## AT-08 --- Canonical location ID produced on in-bound success

**Covers:** Main Scenario Step 6

**Given** - The system is running - Coordinates are valid and within
supported boundary

**When** - The system processes the coordinates

**Then** - A canonical location ID is generated and used for valuation

**Acceptance Criteria** - Canonical ID is non-empty and stable for
repeated identical coordinate inputs (assuming no data version change)

------------------------------------------------------------------------

## AT-09 --- Estimate invariants are maintained

**Covers:** Output integrity

**Given** - The system successfully computes an estimate

**When** - The system returns the estimate response

**Then** - Low value ≤ Estimate ≤ High value - All values are numeric
and non-negative - Output formatting is consistent (e.g., currency
formatting if UI)

**Acceptance Criteria** - Output passes validation rules with no
exceptions
