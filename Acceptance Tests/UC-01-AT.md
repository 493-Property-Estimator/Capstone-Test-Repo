# Acceptance Test Suite --- UC-01 (Enter Street Address)

## Assumptions (for testability)

-   The system exposes an estimate UI or API that accepts a street
    address.
-   A geocoding dependency exists and can be mocked (success / no match
    / outage).
-   The valuation engine can be mocked to return a deterministic
    estimate and range.
-   "Missing open data" can be simulated via feature flags or mocked
    data services.

------------------------------------------------------------------------

## AT-01 --- Successful estimate by valid street address (Happy Path)

**Covers:** Main Success Scenario Steps 1--9

**Given** - The Property Value Estimator system is running - The
geocoding service is available and returns coordinates for the input
address - Required valuation data is available

**When** - The user enters a valid street address and submits the
request

**Then** - The system validates the address format successfully - The
system calls the geocoding service with the entered address - The system
receives valid coordinates - The system normalizes the location into a
canonical location ID - The system computes an estimate - The system
displays: - a single estimated value - a low/high range - The request
completes without errors

**Acceptance Criteria** - A non-empty numeric estimate is shown - Low ≤
Estimate ≤ High - Response time meets the defined SLA (if applicable)

------------------------------------------------------------------------

## AT-02 --- Address format validation fails (Invalid Address Format)

**Covers:** Extension 4a

**Given** - The Property Value Estimator system is running

**When** - The user enters an invalid address format (e.g., missing
street number) and submits

**Then** - The system rejects the address before geocoding - The system
displays a validation error message - The system does not call the
geocoding service - No estimate is shown

**Acceptance Criteria** - Error message is user-actionable (e.g.,
"Include street number and street name") - No external geocoding request
is made

------------------------------------------------------------------------

## AT-03 --- User corrects invalid address and succeeds

**Covers:** Extension 4a2 + return to Main Scenario

**Given** - The Property Value Estimator system is running - Geocoding
service is available and returns coordinates for the corrected address -
Valuation data is available

**When** 1. The user submits an invalid address format 2. The system
shows a validation error 3. The user corrects the address and resubmits

**Then** - The system accepts the corrected address - The system
geocodes successfully - The system returns and displays the estimate and
range

**Acceptance Criteria** - No estimate is shown after the first invalid
submission - Estimate and range are shown after correction

------------------------------------------------------------------------

## AT-04 --- Geocoding returns no match

**Covers:** Extension 6a (no match)

**Given** - The Property Value Estimator system is running - Geocoding
service returns "no match" for the entered address

**When** - The user submits a validly formatted address that does not
exist / cannot be found

**Then** - The system reports that the address could not be
found/verified - The system does not compute an estimate - The system
allows the user to re-enter an address

**Acceptance Criteria** - No estimate is displayed - Message indicates
the address could not be found (not a generic system failure)

------------------------------------------------------------------------

## AT-05 --- Geocoding service outage/failure

**Covers:** Extension 6a (service failure)

**Given** - The Property Value Estimator system is running - Geocoding
service is down or times out

**When** - The user submits a validly formatted address

**Then** - The system displays an error indicating geocoding is
unavailable - The system does not compute an estimate - The system
allows retry or re-entry

**Acceptance Criteria** - No estimate is displayed - Error clearly
distinguishes external service failure vs invalid input

------------------------------------------------------------------------

## AT-06 --- User retries after geocoding failure and succeeds

**Covers:** Extension 6a2 + return to Main Scenario

**Given** - The Property Value Estimator system is running - First
geocoding call fails (timeout/outage) - Subsequent geocoding call
succeeds for the same or updated address - Valuation data is available

**When** 1. The user submits a valid address 2. The system reports
geocoding failure 3. The user retries (or re-submits after editing) 4.
Geocoding succeeds

**Then** - The system computes the estimate - The system displays
estimate and range

**Acceptance Criteria** - The second attempt results in a valid estimate
and range - The system does not remain stuck in an error state

------------------------------------------------------------------------

## AT-07 --- Valuation proceeds with partial open-data unavailable

**Covers:** Extension 8a

**Given** - The Property Value Estimator system is running - Geocoding
succeeds for the entered address - One or more open-data feature sources
are unavailable (simulated) - Baseline assessment data remains available

**When** - The user submits a valid address

**Then** - The system computes a partial estimate - The system displays
estimate and range - The system displays a missing-data warning
indicating reduced accuracy

**Acceptance Criteria** - Estimate and range are shown even with missing
features - Warning is visible and specific (e.g., "Some neighbourhood
features unavailable")

------------------------------------------------------------------------

## AT-08 --- No estimate shown on failure end condition

**Covers:** Failed End Condition (global)

**Given** - The system is running

**When** - The use case ends in failure due to either: - invalid address
not corrected, or - geocoding no match, or - geocoding outage not
resolved

**Then** - The system does not display an estimate value or range - The
system displays a reason for failure and a user next step

**Acceptance Criteria** - UI/API response contains error/warning
content - No numeric estimate output is present

------------------------------------------------------------------------

## AT-09 --- Canonical location ID is produced on geocode success (Internal Acceptance)

**Covers:** Main Scenario Step 7

**Given** - Geocoding succeeds for a valid address

**When** - The system processes the geocoding result

**Then** - A canonical location ID is produced and used for valuation -
The same address submitted twice yields the same canonical location ID
(assuming no underlying data changes)

**Acceptance Criteria** - Canonical ID exists and is non-empty -
Canonical ID is stable across repeated identical requests

------------------------------------------------------------------------

## AT-10 --- Estimate invariants are maintained

**Covers:** Main Scenario output integrity

**Given** - Geocoding and valuation succeed

**When** - The system returns an estimate

**Then** - Low value ≤ Estimate ≤ High value - All values are numeric
and non-negative - Units/formatting are consistent (e.g., currency
formatting if UI)

**Acceptance Criteria** - Output passes validation rules with no
exceptions
