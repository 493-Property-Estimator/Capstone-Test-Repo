# Data Model: UC-07 Amenity Proximity

## Entities

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string)

### Coordinates
- **Fields**:
  - `latitude` (float)
  - `longitude` (float)

### AmenityQuery
- **Fields**:
  - `radius` (number)
  - `categories` (list: `school`, `park`, `hospital`)

### AmenityResult
- **Fields**:
  - `category` (enum: `school`, `park`, `hospital`)
  - `distance` (number)

### ProximityMetrics
- **Fields**:
  - `nearest_school_distance` (number)
  - `parks_within_radius` (integer)
  - `nearest_hospital_distance` (number)
  - `distance_method` (enum: `routing`, `euclidean`)
  - `max_distance_sentinel` (number, optional)

### DesirabilityScore
- **Fields**:
  - `score` (number)
  - `weighting_version` (string)
  - `used_default_weights` (boolean)

### ProximityOutcome
- **Fields**:
  - `status` (enum: `success`, `coordinate_unresolved`)
  - `metrics` (ProximityMetrics, optional)
  - `desirability_score` (DesirabilityScore, optional)
  - `fallback_used` (boolean)
  - `determinism_key` (string, derived from location id + dataset snapshot + config)

## Relationships

- `CanonicalLocation` -> `Coordinates` (1:1)
- `Coordinates` -> `AmenityQuery` (1:1)
- `AmenityQuery` -> `AmenityResult` (0:N)
- `AmenityResult` -> `ProximityMetrics` (1:1 aggregated)
- `ProximityMetrics` -> `DesirabilityScore` (1:1)
- `DesirabilityScore` -> `ProximityOutcome` (1:1)

## State Transitions

1. **Resolved**: Coordinates resolved from canonical location ID.
   - If resolution fails -> `coordinate_unresolved` outcome.
2. **Queried**: Amenities queried within shared radius.
3. **Computed**: Distances computed (routing, fallback to euclidean if needed).
4. **Aggregated**: ProximityMetrics computed.
5. **Scored**: DesirabilityScore derived (default weights if needed).
6. **Attached**: ProximityOutcome attached to property feature set.
