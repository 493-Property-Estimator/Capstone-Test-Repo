# Data Model: UC-11 Commute Accessibility

## Entities

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string)

### EmploymentCenter
- **Fields**:
  - `center_id` (string)
  - `category` (string)
  - `coordinates` (Coordinates)

### Coordinates
- **Fields**:
  - `latitude` (float)
  - `longitude` (float)

### CommuteMetrics
- **Fields**:
  - `nearest_travel_time` (number)
  - `average_travel_time` (number)
  - `weighted_accessibility_index` (number)
  - `distance_method` (enum: `routing`, `euclidean`)
  - `target_count` (integer)

### CommuteAccessibility
- **Fields**:
  - `indicator` (number)
  - `weighting_version` (string)
  - `used_default_weights` (boolean)

### CommuteOutcome
- **Fields**:
  - `status` (enum: `success`, `coordinate_unresolved`, `empty_targets`)
  - `metrics` (CommuteMetrics, optional)
  - `accessibility` (CommuteAccessibility, optional)
  - `fallback_used` (boolean)
  - `absence_marked` (boolean)
  - `determinism_key` (string, derived from location id + dataset snapshot + config)

## Relationships

- `CanonicalLocation` -> `Coordinates` (1:1)
- `EmploymentCenter` -> `Coordinates` (1:1)
- `Coordinates` -> `CommuteMetrics` (1:N aggregated)
- `CommuteMetrics` -> `CommuteAccessibility` (1:1)
- `CommuteAccessibility` -> `CommuteOutcome` (1:1)

## State Transitions

1. **Resolved**: Coordinates resolved for canonical location.
   - If resolution fails -> `coordinate_unresolved` outcome with absence_marked.
2. **Targeted**: Employment centers identified.
   - If none -> `empty_targets` outcome with neutral indicator.
3. **Computed**: Commute metrics computed (routing, fallback to euclidean if needed).
4. **Derived**: Accessibility indicator derived (default weights if needed).
5. **Attached**: CommuteOutcome attached to property feature set.
