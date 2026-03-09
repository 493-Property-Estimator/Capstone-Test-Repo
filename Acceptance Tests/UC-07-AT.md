# Acceptance Test Suite --- UC-07 (Proximity to Amenities → Desirability)

## Assumptions (for testability)

-   The valuation engine exposes a feature computation step (e.g.,
    `compute_proximity_features(canonical_id)`).
-   Canonical ID → coordinates lookup can be mocked (success/fail).
-   POI datasets (schools, parks, hospitals) can be mocked with known
    points.
-   Routing/distance service can be mocked to succeed/fail.
-   Weighting rules can be configured/misconfigured for test purposes.
-   Output contains proximity metrics + desirability score (or indicates
    omission when not computed).

------------------------------------------------------------------------

## AT-01 --- Compute proximity metrics and desirability score (Happy Path)

**Covers:** Main Success Scenario Steps 1--7

**Given** - The system is running - A valid canonical location ID is
provided - Canonical ID resolves to coordinates - POI datasets contain
schools, parks, and hospitals within the configured search radius -
Distance computation (routing or configured method) is available -
Weighting rules are configured

**When** - The valuation engine triggers proximity feature computation

**Then** - The system queries for amenities within the search radius -
The system computes distances to relevant amenities - The system
aggregates proximity metrics (at minimum: nearest school distance, parks
count within radius, nearest hospital distance) - The system derives a
desirability score using weighting rules - The system attaches proximity
metrics + desirability score to the feature set

**Acceptance Criteria** - Proximity metrics are present and numeric -
Desirability score is present and numeric - Feature set contains correct
fields for all configured amenity categories

------------------------------------------------------------------------

## AT-02 --- No amenities found within radius produces fallback values

**Covers:** Extension 3a

**Given** - The system is running - Canonical ID resolves to
coordinates - POI datasets contain no amenities of one or more
categories within the configured radius - Weighting rules are configured

**When** - Proximity feature computation runs

**Then** - The system returns fallback values: - zero counts for count
metrics (e.g., parks_within_radius = 0) - maximum-distance (or sentinel)
values for nearest-distance metrics, per rules - The system still
computes a desirability score using fallback scoring logic - Features
are attached to the feature set

**Acceptance Criteria** - Metrics reflect absence of amenities
deterministically (no nulls unless explicitly designed) - Desirability
score is computed and present

------------------------------------------------------------------------

## AT-03 --- Routing/distance service unavailable triggers Euclidean fallback

**Covers:** Extension 4a

**Given** - The system is running - Canonical ID resolves to
coordinates - POI datasets contain amenities within radius -
Routing-based distance service fails (timeout/outage) - Euclidean
distance fallback is enabled

**When** - Proximity feature computation runs

**Then** - The system logs routing failure and uses Euclidean distance -
The system produces proximity metrics and desirability score - The
system marks that fallback distance method was used (log and/or
metadata)

**Acceptance Criteria** - Metrics and desirability score are present -
Computed distances match Euclidean expectations for the mocked
coordinates (within tolerance) - Fallback usage is recorded

------------------------------------------------------------------------

## AT-04 --- Canonical location ID cannot be resolved to coordinates → omit proximity

**Covers:** Extension 2a

**Given** - The system is running - Canonical ID lookup fails (no
coordinates found / data inconsistency)

**When** - Proximity feature computation runs

**Then** - The system logs the failure - The system does not compute
proximity metrics - The system omits desirability adjustment (or sets to
default neutral, per design) - Downstream valuation continues without
proximity features

**Acceptance Criteria** - Feature set indicates proximity features are
absent (or defaulted explicitly) - No POI or distance service calls
occur after coordinate resolution failure

------------------------------------------------------------------------

## AT-05 --- Weighting rules misconfigured triggers default weights

**Covers:** Extension 6a

**Given** - The system is running - Canonical ID resolves to
coordinates - POI datasets and distance computation work - Weighting
configuration is missing or invalid - Default weights are available

**When** - Proximity feature computation runs

**Then** - The system logs weighting configuration issue - The system
applies default weighting parameters - The system derives a desirability
score and attaches features

**Acceptance Criteria** - Desirability score is present - Metadata/log
indicates default weights were used - Score matches expected output
under default weights (for mocked data)

------------------------------------------------------------------------

## AT-06 --- Proximity metric integrity checks (sanity)

**Covers:** Output quality/invariants

**Given** - Proximity metrics are computed successfully

**When** - The feature set is produced

**Then** - All distance metrics are non-negative numbers - Count metrics
are non-negative integers - Units are consistent (e.g., meters or
kilometers, consistently documented) - Nearest-distance metrics are ≤
configured maximum-distance sentinel (if used)

**Acceptance Criteria** - Output passes validation rules with no
exceptions

------------------------------------------------------------------------

## AT-07 --- Determinism for same inputs

**Covers:** Consistency requirement for valuation features

**Given** - Same canonical location ID - Same POI dataset snapshot -
Same configuration (radius, weights, distance method)

**When** - Proximity computation runs multiple times

**Then** - Proximity metrics and desirability score are identical each
run (within tolerance for floating point)

**Acceptance Criteria** - Results match exactly for integers and within
tolerance for floating values
