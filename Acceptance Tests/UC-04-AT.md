# Acceptance Test Suite --- UC-04 (Normalize to Canonical Location ID)

## Assumptions (for testability)

-   The system exposes a normalization function/endpoint used internally
    (e.g., `normalize(input) → canonical_location_id`).
-   Geocoding can be mocked (success / no match / outage).
-   Boundary validation can be tested with known in-bound and
    out-of-bound coordinates.
-   Spatial database lookups can be mocked (parcel found / not found).
-   Canonical ID generation rules are deterministic and testable.

------------------------------------------------------------------------

## AT-01 --- Normalize address input to canonical location ID (Happy Path -- Address)

**Covers:** Main Success Scenario Steps 1--7 (address branch)

**Given** - The system is running - A valid address is provided -
Geocoding service returns valid coordinates for the address -
Coordinates are within supported boundary - Spatial database returns a
containing parcel/spatial unit

**When** - The system receives the address for normalization

**Then** - The system geocodes the address into coordinates - The system
validates coordinates are in-bound - The system resolves a spatial unit
(e.g., parcel) - The system generates a canonical location ID - The
canonical location ID is returned or forwarded downstream

**Acceptance Criteria** - Canonical location ID is non-empty - Canonical
location ID follows defined format constraints (if any) - Downstream
step receives canonical ID (or response includes it)

------------------------------------------------------------------------

## AT-02 --- Normalize coordinate input to canonical location ID (Happy Path -- Coordinates)

**Covers:** Main Success Scenario Steps 1, 4--7 (coordinates branch)

**Given** - The system is running - Valid in-bound coordinates are
provided - Spatial database returns a containing parcel/spatial unit

**When** - The system receives coordinates for normalization

**Then** - The system validates coordinates are in-bound - The system
resolves a spatial unit - The system generates a canonical location ID -
The canonical location ID is returned or forwarded downstream

**Acceptance Criteria** - Canonical ID is non-empty and stable (see
AT-08) - No geocoding call is made

------------------------------------------------------------------------

## AT-03 --- Geocoding fails or returns no match (Normalization fails)

**Covers:** Extension 2a

**Given** - The system is running - An address is provided - Geocoding
service times out / is unavailable OR returns "no match"

**When** - The system attempts to normalize the address

**Then** - The system logs the failure - The system returns an error
indicating normalization could not be completed - No canonical location
ID is produced - Downstream processing does not proceed

**Acceptance Criteria** - Error is classified as geocoding failure/no
match (not a generic error) - No spatial database lookup occurs after
geocoding failure

------------------------------------------------------------------------

## AT-04 --- Coordinates outside supported boundary are rejected

**Covers:** Extension 4a

**Given** - The system is running - Coordinates (from user input or
geocoding) are outside the supported region

**When** - The system attempts boundary validation during normalization

**Then** - The system logs boundary validation failure - The system
returns an error indicating unsupported location - No canonical location
ID is generated - No downstream processing occurs

**Acceptance Criteria** - No spatial-unit lookup occurs for out-of-bound
coordinates - Error clearly indicates "outside supported area"

------------------------------------------------------------------------

## AT-05 --- No parcel/spatial unit found; fallback spatial unit is assigned

**Covers:** Extension 5a

**Given** - The system is running - Valid in-bound coordinates are
provided - Spatial database returns "no containing parcel / no primary
spatial unit" - Fallback rule is enabled (e.g., grid cell assignment)

**When** - The system attempts spatial resolution

**Then** - The system assigns a fallback spatial unit (e.g., grid
cell) - The system generates a canonical location ID based on the
fallback unit - The canonical ID is returned/forwarded downstream

**Acceptance Criteria** - Canonical ID is non-empty - Canonical ID
identifies fallback unit type (if that is part of the design) -
Normalization completes successfully (not an error)

------------------------------------------------------------------------

## AT-06 --- Fallback assignment is deterministic

**Covers:** Extension 5a determinism

**Given** - Same in-bound coordinates are normalized twice - Spatial
lookup continues to return "no parcel found"

**When** - The system performs normalization twice under identical
conditions

**Then** - The same fallback spatial unit is selected both times - The
same canonical location ID is produced both times

**Acceptance Criteria** - Canonical IDs match exactly for repeated
identical inputs

------------------------------------------------------------------------

## AT-07 --- Canonical ID conflict/duplication detected and resolved

**Covers:** Extension 6a

**Given** - The system is running - Spatial unit is resolved - Canonical
ID generation detects an existing conflicting ID or duplication
condition

**When** - The system attempts to generate the canonical location ID

**Then** - The system applies deterministic conflict resolution rules -
The system produces a stable, unique canonical location ID - The
canonical ID is forwarded downstream

**Acceptance Criteria** - Canonical ID returned is unique under the
system's uniqueness constraints - Conflict resolution does not produce
non-deterministic IDs

------------------------------------------------------------------------

## AT-08 --- Canonical ID stability for identical inputs (Determinism)

**Covers:** Main Scenario Step 6 quality requirement

**Given** - A specific input (address or coordinates) is normalized
multiple times - Underlying spatial datasets have not changed

**When** - The system normalizes the same input repeatedly

**Then** - The canonical location ID is identical each time

**Acceptance Criteria** - IDs match exactly across runs

------------------------------------------------------------------------

## AT-09 --- Equivalent inputs converge to the same canonical ID (Consistency across entry methods)

**Covers:** Purpose of UC-04

**Given** - A known location can be represented by: - a specific street
address, and - the coordinates returned by geocoding that address

**When** - The system normalizes the address - The system normalizes the
equivalent coordinates

**Then** - Both normalization operations return the same canonical
location ID

**Acceptance Criteria** - IDs match exactly (or match by documented
equivalence rule)

------------------------------------------------------------------------

## AT-10 --- No downstream processing proceeds if normalization fails

**Covers:** Failed End Condition enforcement

**Given** - A normalization error occurs (geocoding failure or
out-of-bound location)

**When** - The normalization step ends in failure

**Then** - The valuation engine is not invoked - Feature computation is
not invoked - Caching write does not occur for the failed request

**Acceptance Criteria** - No downstream service calls are made after
normalization failure - Logs/metrics indicate "normalization failed"
outcome
