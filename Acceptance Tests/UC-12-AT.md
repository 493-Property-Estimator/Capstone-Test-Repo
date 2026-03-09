# Acceptance Test Suite --- UC-12 (Neighbourhood Indicators → Local Context)

## Assumptions (for testability)

-   The valuation engine exposes a feature computation function (e.g.,
    `compute_neighbourhood_indicators(canonical_id)`).
-   Canonical ID → coordinates resolution can be mocked (success/fail).
-   Neighbourhood boundary dataset (e.g., census tracts / planning
    districts) can be mocked with deterministic polygons.
-   Statistical datasets (demographics, income, crime, density,
    tenure mix) can be mocked and versioned (snapshot).
-   Fallback logic can be enabled (cached values or regional averages).
-   Composite weighting/threshold configuration can be enabled/disabled
    for tests.
-   Output includes individual neighbourhood indicators and a summarized
    context profile (or indicates omission/defaults when not computed).

------------------------------------------------------------------------

## AT-01 --- Compute neighbourhood indicators and composite profile (Happy Path)

**Covers:** Main Success Scenario Steps 1--7

**Given** - The system is running - A valid canonical location ID is
provided - Canonical ID resolves to property coordinates - Neighbourhood
boundary dataset is available and contains the property point within
exactly one boundary - Statistical datasets are available and contain
indicators for that boundary - Composite scoring/weighting configuration
is present

**When** - The valuation engine triggers neighbourhood context
computation

**Then** - The system maps the property to a neighbourhood boundary -
The system retrieves neighbourhood-level indicators from datasets (per
configured set) - The system normalizes/aggregates indicators as
required - The system derives a summarized neighbourhood context
profile/composite indicator - The system attaches indicators + composite
profile to the property's feature set

**Acceptance Criteria** - Boundary ID/name (or equivalent) is present in
output metadata - All configured indicators are present and non-empty -
Composite profile is present and non-empty (numeric or categorical per
design)

------------------------------------------------------------------------

## AT-02 --- Canonical location cannot be resolved to coordinates → omit neighbourhood features

**Covers:** Extension 2a

**Given** - The system is running - Canonical ID lookup fails (missing
coordinates / inconsistent data)

**When** - Neighbourhood context computation runs

**Then** - The system logs the failure - The system does not attempt
boundary lookup - The system omits neighbourhood indicators and
composite profile (or sets neutral defaults per design)

**Acceptance Criteria** - No boundary dataset calls occur after
coordinate resolution failure - Feature set clearly indicates
neighbourhood features absent or defaulted explicitly

------------------------------------------------------------------------

## AT-03 --- Property on edge / overlaps multiple boundaries → deterministic boundary resolution

**Covers:** Extension 3a

**Given** - The system is running - Canonical ID resolves to coordinates
that lie on a boundary edge or intersect multiple neighbourhood
polygons - Boundary resolution policy is configured (e.g.,
nearest-centroid, largest-overlap, deterministic tie-break rule)

**When** - Neighbourhood boundary resolution runs

**Then** - The system applies the configured resolution policy - The
system logs the resolution method used - The system selects a single
boundary deterministically - The system retrieves indicators for the
resolved boundary and continues normal flow

**Acceptance Criteria** - Selected boundary matches expected boundary
under the configured policy - Resolution method is recorded (log and/or
response metadata) - Indicators and composite profile are produced

------------------------------------------------------------------------

## AT-04 --- Statistical dataset unavailable triggers fallback values + warning/flag

**Covers:** Extension 4a

**Given** - The system is running - Canonical ID resolves to coordinates
and maps to a boundary successfully - One or more statistical datasets
are unavailable/incomplete (simulated) - Fallback values are available
(cached boundary-level values or regional averages)

**When** - Indicator retrieval runs

**Then** - The system logs the dataset issue - The system uses fallback
values for missing indicators - The system derives the composite
neighbourhood context profile using available + fallback values - The
system attaches indicators + composite profile and indicates fallback
usage

**Acceptance Criteria** - Composite profile is present - Missing
indicators are populated via fallback policy (no unexpected nulls unless
explicitly designed) - Output indicates fallback data used (log and/or
response metadata)

------------------------------------------------------------------------

## AT-05 --- Composite weighting configuration missing uses default weights

**Covers:** Extension 6a

**Given** - The system is running - Canonical ID resolves and indicators
are retrieved/normalized successfully - Composite weighting
configuration is missing or invalid - Default composite weights are
available

**When** - Composite profile derivation runs

**Then** - The system logs configuration issue - The system applies
default weights/thresholds - The system produces and attaches a
composite neighbourhood profile

**Acceptance Criteria** - Composite profile is present - Output
indicates defaults were used (log/metadata) - Composite profile matches
expected result under defaults for the mocked indicators

------------------------------------------------------------------------

## AT-06 --- Normalization and range integrity checks (sanity/invariants)

**Covers:** Output quality

**Given** - Indicators are computed and normalized

**When** - Output is produced

**Then** - Normalized indicators fall within expected ranges (e.g., 0--1
or 0--100 where configured) - Raw indicators obey domain constraints
(e.g., density ≥ 0; income ≥ 0) - No NaN/Infinity values appear - Units
are consistent with dataset definitions (e.g., per km², per 1,000
residents)

**Acceptance Criteria** - Output passes validation rules with no
exceptions

------------------------------------------------------------------------

## AT-07 --- Determinism for identical inputs and dataset snapshot

**Covers:** Reproducibility/caching consistency

**Given** - Same canonical location ID - Same boundary dataset
snapshot - Same statistical dataset snapshot(s) - Same normalization
rules and composite configuration

**When** - Neighbourhood context computation runs multiple times

**Then** - Boundary selection, indicators, and composite profile are
identical across runs (within tolerance for floating point)

**Acceptance Criteria** - Exact match for categorical outputs; within
tolerance for numeric outputs
