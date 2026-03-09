# Acceptance Test Suite --- UC-11 (Commute Accessibility → Work Access)

## Assumptions (for testability)

-   The valuation engine exposes a feature computation function (e.g.,
    `compute_commute_accessibility(canonical_id)`).
-   Canonical ID → coordinates resolution can be mocked (success/fail).
-   Employment center dataset can be mocked with known destinations
    (CBD, hubs, etc.).
-   Routing service can be mocked (success/failure/timeout).
-   Euclidean fallback can be enabled/disabled.
-   Weighting/threshold configuration can be enabled/disabled.
-   Output includes commute metrics and a derived commute accessibility
    indicator (or indicates omission/defaults when not computed).

------------------------------------------------------------------------

## AT-01 --- Compute commute travel metrics and accessibility indicator (Happy Path)

**Covers:** Main Success Scenario Steps 1--8

**Given** - The system is running - A valid canonical location ID is
provided - Canonical ID resolves to property coordinates - Employment
centers are configured and available in the dataset - Routing service is
available and configured (transport mode defined) - Weighting/threshold
rules are configured

**When** - The valuation engine triggers commute accessibility
computation

**Then** - The system identifies configured employment centers/targets -
The system computes travel time/distance to each target via routing -
The system aggregates commute metrics (e.g., nearest time, average to
top N, weighted index) - The system derives a commute accessibility
indicator using thresholds/weights - The system attaches commute
metrics + indicator to the feature set

**Acceptance Criteria** - Travel metrics are numeric and non-negative -
Aggregated metrics are present and numeric - Commute accessibility
indicator is present and non-empty (numeric or categorical per design) -
Units are consistent (minutes/seconds for time; km/m for distance)

------------------------------------------------------------------------

## AT-02 --- Canonical location cannot be resolved to coordinates → omit commute features

**Covers:** Extension 2a

**Given** - The system is running - Canonical ID lookup fails (missing
coordinates / data inconsistency)

**When** - Commute accessibility computation runs

**Then** - The system logs the failure - The system does not query
employment centers or call routing - The system omits commute features
(or sets neutral defaults per design)

**Acceptance Criteria** - No routing calls occur after coordinate
resolution failure - Feature set clearly indicates commute features
absent or defaulted explicitly

------------------------------------------------------------------------

## AT-03 --- No employment centers configured or found → neutral/default accessibility values

**Covers:** Extension 3a

**Given** - The system is running - Canonical ID resolves to
coordinates - Employment center configuration is empty OR dataset query
returns none

**When** - Commute accessibility computation runs

**Then** - The system records default/neutral commute accessibility
values per policy (e.g., neutral index, null/empty metrics) - The system
logs the configuration issue

**Acceptance Criteria** - Output follows defined empty-target policy
deterministically - No routing calls are made when there are no targets

------------------------------------------------------------------------

## AT-04 --- Routing service unavailable/timeout triggers Euclidean fallback

**Covers:** Extension 4a

**Given** - The system is running - Canonical ID resolves to
coordinates - Employment centers are available - Routing-based travel
metrics are configured as primary method - Routing service fails
(timeout/outage) - Euclidean fallback is enabled

**When** - Commute accessibility computation runs

**Then** - The system logs routing failure - The system computes
Euclidean distances to employment centers - The system aggregates
fallback distances into commute metrics - The system derives the commute
accessibility indicator using fallback metrics - The system records that
fallback was used (log/metadata)

**Acceptance Criteria** - Commute metrics and indicator are present -
Distances match Euclidean expectations for mocked points (within
tolerance) - Fallback usage is recorded

------------------------------------------------------------------------

## AT-05 --- Weighting/threshold configuration missing uses default commute weights

**Covers:** Extension 7a

**Given** - The system is running - Canonical ID resolves to
coordinates - Commute travel metrics compute successfully -
Weighting/threshold configuration is missing or invalid - Default
commute weights exist

**When** - Commute accessibility indicator derivation runs

**Then** - The system logs configuration issue - The system applies
default weights/thresholds - The system derives and attaches the commute
accessibility indicator

**Acceptance Criteria** - Indicator is present - Output indicates
defaults were used (log/metadata) - Indicator matches expected output
for mocked metrics under defaults

------------------------------------------------------------------------

## AT-06 --- Metric integrity checks (sanity/invariants)

**Covers:** Output quality

**Given** - Commute metrics are computed (routing or fallback)

**When** - Feature output is produced

**Then** - All times/distances are non-negative - If "nearest" and
"average" are computed on the same set: nearest ≤ average - Units are
consistent across all commute metrics - No NaN/Infinity values appear

**Acceptance Criteria** - Output passes validation rules with no
exceptions

------------------------------------------------------------------------

## AT-07 --- Determinism for identical inputs and configuration

**Covers:** Reproducibility/caching consistency

**Given** - Same canonical location ID - Same employment center dataset
snapshot - Same routing configuration (mode, time-of-day assumptions if
any) - Same thresholds/weights

**When** - Commute accessibility computation runs multiple times

**Then** - Commute metrics and accessibility indicator are identical
across runs (within tolerance for floating point)

**Acceptance Criteria** - Exact match for categorical outputs; within
tolerance for numeric outputs
