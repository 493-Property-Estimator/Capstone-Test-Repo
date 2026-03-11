# Data Model: UC-10 School Distance Signals

## Entities

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string)

### School
- **Fields**:
  - `school_id` (string)
  - `category` (enum: `elementary`, `secondary`, `other`)
  - `coordinates` (Coordinates)

### Coordinates
- **Fields**:
  - `latitude` (float)
  - `longitude` (float)

### SchoolDistanceMetrics
- **Fields**:
  - `nearest_elementary_distance` (number)
  - `nearest_secondary_distance` (number)
  - `average_distance_top_n` (number)
  - `distance_method` (enum: `routing`, `euclidean`)
  - `sentinel_value_used` (boolean)

### FamilySuitability
- **Fields**:
  - `signal` (number)
  - `weighting_version` (string)
  - `used_default_weights` (boolean)

### SchoolDistanceOutcome
- **Fields**:
  - `status` (enum: `success`, `coordinate_unresolved`)
  - `metrics` (SchoolDistanceMetrics, optional)
  - `family_suitability` (FamilySuitability, optional)
  - `fallback_used` (boolean)
  - `absence_marked` (boolean)
  - `determinism_key` (string, derived from location id + school dataset snapshot + config)

## Relationships

- `CanonicalLocation` -> `Coordinates` (1:1)
- `School` -> `Coordinates` (1:1)
- `Coordinates` -> `SchoolDistanceMetrics` (1:N aggregated)
- `SchoolDistanceMetrics` -> `FamilySuitability` (1:1)
- `FamilySuitability` -> `SchoolDistanceOutcome` (1:1)

## State Transitions

1. **Resolved**: Coordinates resolved for canonical location.
   - If resolution fails -> `coordinate_unresolved` outcome with absence_marked.
2. **Queried**: Schools queried within search radius and grouped.
3. **Computed**: Distances computed (routing, fallback to euclidean if needed).
4. **Derived**: Suitability signal derived (default weights if needed).
5. **Attached**: SchoolDistanceOutcome attached to property feature set.
