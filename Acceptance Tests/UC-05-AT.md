# Acceptance Test Suite --- UC-05 (Estimate Using Location Only)

## Assumptions (for testability)

-   The system accepts a "location-only" request through UI or API
    (address / coordinates / map click) with no additional property
    attributes.
-   Normalization (UC-04) can be mocked to succeed or fail.
-   Baseline assessment data lookup can be mocked to succeed or fail.
-   Fallback spatial average lookup can be mocked.
-   The system provides a visible indicator that the estimate is
    location-only.

------------------------------------------------------------------------

## AT-01 --- Location-only estimate succeeds with baseline + location-derived features (Happy Path)

**Covers:** Main Success Scenario Steps 1--7

**Given** - The system is running - A valid location input is provided
(address, coordinates, or map click) - Normalization succeeds and
returns a canonical location ID - Baseline assessment data exists for
the canonical location - Location-derived features are available - No
additional attributes (size/beds/baths) are provided

**When** - The user submits the location-only estimate request

**Then** - The system detects the request contains location input only -
The system retrieves baseline assessment data and location-derived
features - The system computes an estimate - The system computes a
low/high range reflecting higher uncertainty - The system displays: - a
single estimated value - a low/high range - a visible "location-only"
indicator (limited input / reduced accuracy)

**Acceptance Criteria** - Estimate is numeric and non-empty - Low ≤
Estimate ≤ High - "Location-only" indicator is visible in UI or returned
in response metadata

------------------------------------------------------------------------

## AT-02 --- Location normalization failure prevents estimate

**Covers:** Extension 2a

**Given** - The system is running - A location input is provided -
Normalization fails (e.g., invalid address, out-of-bound coordinates,
geocoding failure)

**When** - The user submits the location-only request

**Then** - The system returns an error indicating the location could not
be processed - The system does not compute an estimate - The system does
not display value/range

**Acceptance Criteria** - No estimate fields present in response/UI -
Error message explains failure in actionable terms (e.g., re-enter
location)

------------------------------------------------------------------------

## AT-03 --- Baseline assessment data missing triggers fallback estimate + warning

**Covers:** Extension 4a

**Given** - The system is running - A valid location input is provided -
Normalization succeeds and returns a canonical location ID - Baseline
assessment data is unavailable for this canonical location - Fallback
spatial averages (grid/neighbourhood) are available

**When** - The user submits the location-only estimate request

**Then** - The system attempts baseline retrieval and detects it is
missing - The system computes an estimate using fallback spatial
averages and available location-derived features - The system displays
estimate and range - The system displays a warning that fallback data
was used and accuracy may be reduced

**Acceptance Criteria** - Estimate and range are present - Warning is
visible and specific (not generic) - Response metadata indicates
fallback source used (if API)

------------------------------------------------------------------------

## AT-04 --- Baseline missing and fallback missing results in failure (Insufficient Data)

**Covers:** Extension 5a

**Given** - The system is running - A valid location input is provided -
Normalization succeeds and returns a canonical location ID - Baseline
assessment data is unavailable - Fallback spatial averages are also
unavailable (or insufficient)

**When** - The user submits the location-only estimate request

**Then** - The system determines an estimate cannot be generated
reliably - The system informs the user there is insufficient data to
generate an estimate - No estimate value/range is displayed

**Acceptance Criteria** - No estimate fields in response/UI - Error
clearly states insufficient data (not input validation)

------------------------------------------------------------------------

## AT-05 --- Location-only indicator is present whenever attributes are absent

**Covers:** Main Scenario Step 7 integrity requirement

**Given** - The system is running - A valid location-only request is
submitted (no size/beds/baths)

**When** - The estimate response is returned

**Then** - The response includes a clear indication it is location-only
(limited input) - The UI shows the indicator prominently near the
estimate

**Acceptance Criteria** - Indicator present in all location-only success
responses, including fallback estimate paths

------------------------------------------------------------------------

## AT-06 --- Range reflects higher uncertainty for location-only (Business rule)

**Covers:** UC-05's intent

**Given** - The system is running - A location-only request succeeds - A
comparable "standard input" request exists for the same location (with
attributes)

**When** - The system returns both estimates (location-only vs standard)

**Then** - The location-only estimate range is equal to or wider than
the standard-input range

**Acceptance Criteria** - (High−Low)\_location-only ≥
(High−Low)\_standard-input

------------------------------------------------------------------------

## AT-07 --- Estimate invariants are maintained

**Covers:** Output integrity

**Given** - A location-only estimate is computed successfully

**When** - The system returns the estimate

**Then** - Low value ≤ Estimate ≤ High value - All values are numeric
and non-negative - Output formatting is consistent (e.g., currency
formatting if UI)

**Acceptance Criteria** - Output passes validation rules with no
exceptions
