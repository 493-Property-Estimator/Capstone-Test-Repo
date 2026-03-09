# Acceptance Test Suite --- UC-09 (Green Space Coverage)

## Assumptions (for testability)

-   The valuation engine exposes a feature computation function (e.g.,
    `compute_green_space_features(canonical_id)`).
-   Canonical ID → geometry/coordinates lookup can be mocked
    (success/fail).
-   Land use / green space dataset can be mocked with known polygons.
-   GIS intersection/area calculations can be validated with
    deterministic test geometries.
-   Threshold/weighting configuration can be enabled/disabled for tests.
-   Output includes: green space area, coverage percent, and derived
    environmental desirability indicator (or indicates omission when not
    computed).

------------------------------------------------------------------------

## AT-01 --- Compute green space coverage and desirability indicator (Happy Path)

**Covers:** Main Success Scenario Steps 1--8

**Given** - The system is running - A valid canonical location ID is
provided - Canonical ID resolves to spatial geometry (point or parcel
boundary) - Land use dataset is available and contains green space
polygons overlapping the analysis buffer - GIS processing service is
operational - Threshold/weighting configuration is present

**When** - The valuation engine triggers green space coverage
computation

**Then** - The system defines the configured analysis buffer around the
property - The system queries green space polygons intersecting the
buffer - The system computes total green space area within buffer - The
system computes coverage percentage - The system derives environmental
desirability indicator using thresholds/weights - The system attaches
green space features to the feature set

**Acceptance Criteria** - Green space area is numeric and ≥ 0 - Coverage
percent is numeric and within \[0, 100\] - Environmental desirability
indicator is present and non-empty (numeric or categorical per design)

------------------------------------------------------------------------

## AT-02 --- Canonical location cannot be resolved to geometry → omit green space features

**Covers:** Extension 2a

**Given** - The system is running - Canonical ID lookup fails (no
geometry/coordinates found)

**When** - Green space feature computation runs

**Then** - The system logs the failure - The system does not define a
buffer or query land use polygons - The system omits green space
features (or sets neutral defaults per design) - Downstream valuation
proceeds without environmental adjustment

**Acceptance Criteria** - No land use dataset calls occur after geometry
resolution failure - Feature set clearly indicates features absent or
defaulted explicitly

------------------------------------------------------------------------

## AT-03 --- Land use dataset unavailable triggers fallback averages + warning

**Covers:** Extension 4a

**Given** - The system is running - Canonical ID resolves to geometry -
Land use dataset is unavailable/incomplete (simulated) - Fallback values
are available (cached or regional averages)

**When** - Green space computation runs

**Then** - The system logs dataset issue - The system retrieves fallback
green space coverage values (cached or regional averages) - The system
derives desirability indicator using fallback values - The system
attaches green space features with a warning/flag indicating fallback
usage

**Acceptance Criteria** - Coverage percent and desirability indicator
are present - Output indicates fallback data used (log and/or response
metadata)

------------------------------------------------------------------------

## AT-04 --- No green space within buffer yields zero coverage and low desirability

**Covers:** Extension 4b

**Given** - The system is running - Canonical ID resolves to geometry -
Land use dataset is available - There are no green space polygons
intersecting the analysis buffer

**When** - Green space computation runs

**Then** - The computed green space area is 0 - Coverage percent is 0% -
The desirability indicator reflects the configured "low desirability"
outcome for zero coverage - Features are attached to the feature set

**Acceptance Criteria** - Area == 0 - Coverage == 0 (or 0.0, per
formatting) - Desirability indicator matches defined thresholds for zero
coverage

------------------------------------------------------------------------

## AT-05 --- Threshold/weighting configuration missing uses default parameters

**Covers:** Extension 7a

**Given** - The system is running - Canonical ID resolves to geometry -
Land use dataset is available and GIS processing succeeds -
Threshold/weighting configuration is missing or invalid - Default
weighting parameters are available

**When** - Green space computation runs

**Then** - The system logs configuration issue - The system applies
default environmental thresholds/weights - The system derives
desirability indicator and attaches features

**Acceptance Criteria** - Desirability indicator is present - Output
indicates default config was used (log/metadata) - Score/category
matches expected result under default thresholds for the mocked coverage

------------------------------------------------------------------------

## AT-06 --- Coverage computation integrity checks (sanity)

**Covers:** Output quality/invariants

**Given** - GIS computation completes successfully

**When** - Feature output is produced

**Then** - Coverage percent is within \[0, 100\] - Green space area
within buffer ≤ total buffer area - No negative areas or NaN values
appear

**Acceptance Criteria** - Output passes validation rules with no
exceptions

------------------------------------------------------------------------

## AT-07 --- Determinism for identical inputs and dataset snapshot

**Covers:** Reproducibility/caching consistency

**Given** - Same canonical location ID - Same analysis buffer
configuration - Same land use dataset snapshot - Same
threshold/weighting configuration

**When** - Green space computation runs multiple times

**Then** - Area, coverage percent, and desirability indicator are
identical (within tolerance for floating point)

**Acceptance Criteria** - Exact match for categorical outputs; within
tolerance for numeric outputs
