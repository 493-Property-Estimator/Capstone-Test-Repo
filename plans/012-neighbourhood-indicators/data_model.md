# Data Model: UC-12 Neighbourhood Indicators

## Entities

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string)

### NeighbourhoodBoundary
- **Fields**:
  - `boundary_id` (string)
  - `boundary_name` (string, optional)

### BoundaryResolution
- **Fields**:
  - `policy` (string)
  - `method_used` (string)

### IndicatorSet
- **Fields**:
  - `indicators` (map of name -> value)
  - `normalized` (map of name -> value)

### NeighbourhoodProfile
- **Fields**:
  - `profile_score` (number)
  - `weighting_version` (string)
  - `used_default_weights` (boolean)

### NeighbourhoodOutcome
- **Fields**:
  - `status` (enum: `success`, `coordinate_unresolved`, `fallback_used`)
  - `boundary` (NeighbourhoodBoundary, optional)
  - `indicators` (IndicatorSet, optional)
  - `profile` (NeighbourhoodProfile, optional)
  - `fallback_used` (boolean)
  - `absence_marked` (boolean)
  - `determinism_key` (string, derived from location id + dataset snapshots + config)

## Relationships

- `CanonicalLocation` -> `NeighbourhoodBoundary` (1:1)
- `NeighbourhoodBoundary` -> `IndicatorSet` (1:1)
- `IndicatorSet` -> `NeighbourhoodProfile` (1:1)
- `NeighbourhoodProfile` -> `NeighbourhoodOutcome` (1:1)

## State Transitions

1. **Resolved**: Coordinates resolved and boundary selected deterministically.
   - If resolution fails -> `coordinate_unresolved` outcome with absence_marked.
2. **Retrieved**: Indicators retrieved (fallback values if needed).
3. **Normalized**: Indicators normalized.
4. **Profiled**: Composite profile derived (default weights if needed).
5. **Attached**: NeighbourhoodOutcome attached to property feature set.
