# Acceptance Test Suite --- UC-10 (Distance-to-School → Family Suitability)

## Assumptions (for testability)

-   The valuation engine exposes a feature computation function (e.g.,
    `compute_school_proximity_features(canonical_id)`).
-   Canonical ID → coordinates resolution can be mocked (success/fail).
-   School dataset can be mocked with known school points and categories
    (elementary/middle/high or "secondary").
-   Distance method can be configured (routing-based vs Euclidean) and
    routing can be mocked (success/fail).
-   Threshold/weighting configuration can be enabled/disabled for tests.
-   Output includes school distance metrics and a derived family
    suitability signal (or indicates omission when not computed).

------------------------------------------------------------------------

## AT-01 --- Compute school distance metrics and family suitability (Happy Path)

**Covers:** Main Success Scenario Steps 1--7

**Given** - The system is running - A valid canonical location ID is
provided - Canonical ID resolves to property coordinates - School
dataset is available and contains schools within the configured search
radius - Distance computation is available (routing or configured
method) - Threshold/weighting rules are configured

**When** - The valuation engine triggers school distance computation

**Then** - The system queries schools within the search radius - The
system computes distances to identified schools - The system derives
required metrics (at minimum: nearest elementary, nearest
secondary/high, average to nearest N as configured) - The system derives
a family suitability signal using thresholds/weights - The system
attaches metrics + suitability signal to the feature set

**Acceptance Criteria** - Distances are numeric and non-negative -
Family suitability signal is present and non-empty (numeric or
categorical per design) - Metric fields exist for all configured school
categories

------------------------------------------------------------------------

## AT-02 --- Canonical location cannot be resolved to coordinates → omit school features

**Covers:** Extension 2a

**Given** - The system is running - Canonical ID lookup fails (missing
coordinates / inconsistent data)

**When** - School proximity computation runs

**Then** - The system logs the failure - The system does not query the
school dataset - The system omits school distance metrics and family
suitability adjustment (or sets neutral defaults per design)

**Acceptance Criteria** - No school dataset or routing calls occur after
coordinate resolution failure - Feature set clearly indicates school
features absent or defaulted explicitly

------------------------------------------------------------------------

## AT-03 --- No schools found within radius produces sentinel/max-distance + low suitability

**Covers:** Extension 3a

**Given** - The system is running - Canonical ID resolves to
coordinates - School dataset is available - No schools exist within the
configured search radius

**When** - School proximity computation runs

**Then** - The system records maximum-distance or sentinel values for
nearest-school metrics per policy - The system records counts as zero if
applicable - The system derives a low family suitability signal
consistent with thresholds - The system attaches the metrics +
suitability signal

**Acceptance Criteria** - Sentinel/max-distance values match configured
policy exactly - Suitability signal matches configured "low" outcome for
zero nearby schools

------------------------------------------------------------------------

## AT-04 --- Routing service unavailable triggers Euclidean fallback (if routing is configured)

**Covers:** Extension 4a

**Given** - The system is running - Canonical ID resolves to
coordinates - Schools exist within radius - Routing-based distance is
configured as primary method - Routing service fails (timeout/outage) -
Euclidean fallback is enabled

**When** - School proximity computation runs

**Then** - The system logs routing failure - The system computes
Euclidean distances to schools - The system derives metrics and
suitability signal using fallback distances - The system records that
fallback distance method was used (log/metadata)

**Acceptance Criteria** - Metrics and suitability signal are present -
Distances match Euclidean expectations for mocked points (within
tolerance) - Fallback usage is recorded

------------------------------------------------------------------------

## AT-05 --- Threshold/weighting configuration missing uses default parameters

**Covers:** Extension 6a

**Given** - The system is running - Canonical ID resolves to
coordinates - School distance metrics compute successfully -
Threshold/weighting configuration is missing or invalid - Default
thresholds/weights exist

**When** - Family suitability signal derivation runs

**Then** - The system logs configuration issue - The system applies
default thresholds/weights - The system derives and attaches the family
suitability signal

**Acceptance Criteria** - Suitability signal present - Output indicates
defaults were used (log/metadata) - Signal matches expected result under
default configuration for the mocked distances

------------------------------------------------------------------------

## AT-06 --- Metric integrity checks (sanity/invariants)

**Covers:** Output quality

**Given** - School metrics are computed (routing or fallback)

**When** - Feature set is produced

**Then** - All distance values are ≥ 0 - Any "average distance" is ≥
"nearest distance" when computed on the same set - Units are consistent
across metrics (meters/km or seconds/minutes as configured) - Sentinel
values appear only when applicable (no schools / unreachable)

**Acceptance Criteria** - Output passes validation rules with no
exceptions

------------------------------------------------------------------------

## AT-07 --- Determinism for identical inputs and dataset snapshot

**Covers:** Reproducibility/caching consistency

**Given** - Same canonical location ID - Same school dataset snapshot -
Same configuration (radius, distance method, thresholds/weights)

**When** - Computation runs multiple times

**Then** - Distance metrics and family suitability signal are identical
across runs (within tolerance for floating point)

**Acceptance Criteria** - Exact match for categorical outputs; within
tolerance for numeric outputs
