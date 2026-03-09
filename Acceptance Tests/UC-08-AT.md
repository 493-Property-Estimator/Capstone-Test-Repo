# Acceptance Test Suite --- UC-08 (Travel-Based Distance for Accessibility)

## Assumptions (for testability)

-   The valuation engine exposes a feature computation function (e.g.,
    `compute_travel_accessibility(canonical_id, destinations)`).
-   Canonical ID → coordinates resolution can be mocked (success/fail).
-   Destination coordinates are available (or can be mocked).
-   Routing service can be mocked (success/timeout/unreachable).
-   Euclidean fallback can be enabled/disabled for tests.
-   Output includes travel-based metrics (distance and/or time) and
    derived accessibility features (aggregations).

------------------------------------------------------------------------

## AT-01 --- Compute travel-based distances for destinations (Happy Path)

**Covers:** Main Success Scenario Steps 1--7

**Given** - The system is running - A valid canonical location ID is
provided - Canonical ID resolves to property coordinates - Destination
set is non-empty and each destination has valid coordinates - Routing
service is available and configured (including transport mode) - Road
network data is available/indexed

**When** - The valuation engine requests travel-based distances for the
property to all destinations

**Then** - The system invokes the routing service for each
origin--destination pair (or in batches) - Travel-based distances
(and/or travel times) are returned - The system aggregates travel-based
metrics (e.g., nearest travel time, average travel time, min distance) -
The system attaches travel-based accessibility features to the
property's feature set

**Acceptance Criteria** - Travel metrics are present and numeric -
Aggregated accessibility metrics are present and numeric - Units are
consistent (e.g., seconds/minutes for time; meters/km for distance)

------------------------------------------------------------------------

## AT-02 --- Canonical location ID cannot be resolved to coordinates → omit travel features

**Covers:** Extension 2a

**Given** - The system is running - Canonical ID lookup fails (missing
coordinates / data inconsistency) - Destination set may be valid

**When** - Travel-based distance computation is requested

**Then** - The system logs the failure - The system does not call the
routing service - The system omits travel-based accessibility features
(or sets neutral defaults per design) - Downstream valuation proceeds
without travel-based adjustments

**Acceptance Criteria** - No routing calls occur after coordinate
resolution failure - Feature set clearly indicates travel-based features
absent or defaulted explicitly

------------------------------------------------------------------------

## AT-03 --- Routing service timeout/unavailable triggers Euclidean fallback

**Covers:** Extension 4a

**Given** - The system is running - Property coordinates resolve
successfully - Destination set is non-empty and valid - Routing service
fails (timeout/outage) - Euclidean fallback is enabled

**When** - Travel-based distance computation runs

**Then** - The system logs routing failure - The system computes
Euclidean distances between property and destinations - The system
aggregates fallback metrics into accessibility features - The system
attaches fallback-based accessibility features

**Acceptance Criteria** - Accessibility features are produced despite
routing failure - Output indicates fallback method used (log and/or
response metadata) - Distances match Euclidean expectations for mocked
coordinates (within tolerance)

------------------------------------------------------------------------

## AT-04 --- No viable travel path found returns sentinel/threshold values

**Covers:** Extension 4b

**Given** - The system is running - Property coordinates and destination
coordinates are valid - Routing service is available - For one or more
destinations, routing service returns "unreachable/no path" -
Sentinel/threshold policy is configured (e.g., `MAX_TRAVEL_TIME`,
`MAX_TRAVEL_DISTANCE`)

**When** - Travel-based distance computation runs

**Then** - The system records sentinel/threshold values for unreachable
routes - The system continues aggregation using these values - The
system attaches accessibility features reflecting limited connectivity

**Acceptance Criteria** - Unreachable destinations are handled without
failing the whole computation - Sentinel values follow configured
thresholds exactly - Aggregations include sentinel values per documented
aggregation rules

------------------------------------------------------------------------

## AT-05 --- Destination list empty yields default/neutral accessibility metrics

**Covers:** Extension 6a

**Given** - The system is running - Canonical ID resolves to
coordinates - Destination list is empty

**When** - Travel-based accessibility computation runs

**Then** - The system does not call the routing service - The system
records default/neutral accessibility metrics (zero-count/null/default
per rule) - The system logs the configuration/upstream issue (if
applicable)

**Acceptance Criteria** - Output metrics follow defined
empty-destination policy deterministically - No routing calls are made

------------------------------------------------------------------------

## AT-06 --- Metric integrity checks (sanity/invariants)

**Covers:** Output quality

**Given** - Travel-based metrics are computed (routing or fallback)

**When** - The feature set is produced

**Then** - All distances/times are non-negative - Aggregated metrics
obey expected relationships (e.g., nearest ≤ average when applicable) -
Sentinel values appear only when route unreachable (not randomly) -
Units are consistent across all outputs

**Acceptance Criteria** - Output passes validation rules with no
exceptions

------------------------------------------------------------------------

## AT-07 --- Determinism for identical inputs and configuration

**Covers:** Consistency for caching/reproducibility

**Given** - Same canonical location ID - Same destination list and
coordinates - Same routing configuration (mode, weighting, time-of-day
assumptions if any) - Same road network snapshot

**When** - Travel-based distance computation is run multiple times

**Then** - Results are identical across runs (within tolerance for
floating point) - Aggregated accessibility metrics match across runs

**Acceptance Criteria** - Exact match for integer fields; within
tolerance for floating values
