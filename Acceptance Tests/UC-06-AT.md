# Acceptance Test Suite --- UC-06 (Provide Basic Property Details)

## Assumptions (for testability)

-   The system accepts a request containing: location + optional
    attributes (`size`, `beds`, `baths`).
-   Normalization (UC-04) can be mocked to succeed or fail.
-   Baseline assessment + feature retrieval can be mocked (available /
    partial).
-   The valuation engine can be mocked to ensure deterministic
    comparisons.
-   The system indicates when user-provided attributes were
    incorporated.

------------------------------------------------------------------------

## AT-01 --- Successful refined estimate with valid size/beds/baths (Happy Path)

**Covers:** Main Success Scenario Steps 1--9

**Given** - The system is running - A valid location input is provided -
Normalization succeeds and returns a canonical location ID - Baseline
assessment and location-derived features are available - User provides
valid attributes: - `size` is positive numeric - `beds` and `baths` are
non-negative numeric

**When** - The user submits the estimate request with location +
attributes

**Then** - The system validates all provided attributes successfully -
The system retrieves baseline + features - The system applies
attribute-based adjustments - The system returns: - a single estimated
value - a low/high range - a visible indication that user attributes
were incorporated

**Acceptance Criteria** - Estimate is numeric and non-empty - Low ≤
Estimate ≤ High - Attribute-incorporation indicator is present in
UI/response metadata

------------------------------------------------------------------------

## AT-02 --- Location normalization failure prevents estimate

**Covers:** Extension 2a

**Given** - The system is running - A location input and attributes are
provided - Normalization fails (e.g., geocoding failure / out-of-bound
location)

**When** - The user submits the request

**Then** - The system returns an error indicating location could not be
processed - The system does not compute an estimate - No value/range is
displayed

**Acceptance Criteria** - No estimate fields present in response/UI - No
valuation engine call occurs after normalization failure

------------------------------------------------------------------------

## AT-03 --- Negative or non-numeric size is rejected

**Covers:** Extension 4a (size validation)

**Given** - The system is running - Location normalization succeeds -
`size` is invalid (negative, zero, or non-numeric) - Other attributes
may be valid

**When** - The user submits the request

**Then** - The system rejects the request with a validation error for
`size` - The system does not compute an estimate - The system provides
an actionable error message

**Acceptance Criteria** - Error message states size must be a positive
number - No valuation computation occurs

------------------------------------------------------------------------

## AT-04 --- Negative or non-numeric beds/baths are rejected

**Covers:** Extension 4a (beds/baths validation)

**Given** - The system is running - Location normalization succeeds -
`beds` or `baths` is invalid (negative or non-numeric)

**When** - The user submits the request

**Then** - The system rejects the request with a validation error - The
system does not compute an estimate - The system provides an actionable
error message

**Acceptance Criteria** - Error message states beds/baths must be
non-negative numbers - No valuation computation occurs

------------------------------------------------------------------------

## AT-05 --- User corrects invalid attributes and succeeds

**Covers:** Extension 4a3 + return to Main Scenario

**Given** - The system is running - Location normalization succeeds -
First submission contains invalid attributes - Second submission
contains corrected valid attributes - Baseline + features are available

**When** 1. User submits invalid attributes 2. System displays
validation errors 3. User corrects attributes and resubmits

**Then** - First attempt returns validation error with no estimate -
Second attempt returns estimate and range with attributes incorporated

**Acceptance Criteria** - No estimate shown after first attempt -
Estimate and range shown after correction

------------------------------------------------------------------------

## AT-06 --- Partial attribute set provided still produces estimate

**Covers:** Extension 6a

**Given** - The system is running - Location normalization succeeds -
Baseline + features are available - User provides only a subset of
attributes (e.g., size only; beds missing)

**When** - The user submits the request

**Then** - The system validates provided fields - The system computes an
estimate using available attributes - The system indicates only some
attributes were incorporated (or clearly indicates which)

**Acceptance Criteria** - Estimate and range are produced - UI/response
reflects partial attribute usage

------------------------------------------------------------------------

## AT-07 --- Missing baseline/features triggers warning but still computes estimate

**Covers:** Extension 7a

**Given** - The system is running - Location normalization succeeds -
User attributes are valid - Some baseline or feature data is unavailable
(simulated) - Minimum required data remains available to compute an
estimate

**When** - The user submits the request

**Then** - The system computes an estimate using available data + user
attributes - The system displays estimate and range - The system
displays a warning indicating reduced accuracy due to missing data

**Acceptance Criteria** - Estimate and range are present - Warning is
visible and specific

------------------------------------------------------------------------

## AT-08 --- Range is narrower than location-only estimate for same location (Improved precision rule)

**Covers:** UC-06 intent

**Given** - The system is running - Same location is used for two
requests: 1) location-only (UC-05 style) 2) location + valid attributes
(UC-06) - Both requests succeed

**When** - The system returns both estimates

**Then** - The attribute-based estimate range is equal to or narrower
than the location-only range

**Acceptance Criteria** - (High−Low)\_with-attributes ≤
(High−Low)\_location-only

------------------------------------------------------------------------

## AT-09 --- Estimate invariants are maintained

**Covers:** Output integrity

**Given** - The system successfully computes an estimate with attributes

**When** - The system returns the estimate response

**Then** - Low value ≤ Estimate ≤ High value - Values are numeric and
non-negative - Output formatting is consistent (e.g., currency
formatting if UI)

**Acceptance Criteria** - Output passes validation rules with no
exceptions
