# Data Model: UC-08 Travel Accessibility

## Entities

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string)

### Destination
- **Fields**:
  - `destination_id` (string)
  - `category` (string)
  - `coordinates` (Coordinates)

### Coordinates
- **Fields**:
  - `latitude` (float)
  - `longitude` (float)

### TravelRoute
- **Fields**:
  - `travel_time` (number)
  - `travel_distance` (number, optional)
  - `route_status` (enum: `ok`, `unreachable`, `fallback_euclidean`)

### AccessibilityMetrics
- **Fields**:
  - `nearest_travel_time` (number)
  - `average_travel_time` (number)
  - `sentinel_value_used` (boolean)
  - `distance_method` (enum: `routing`, `euclidean`)

### AccessibilityOutcome
- **Fields**:
  - `status` (enum: `success`, `coordinate_unresolved`)
  - `metrics` (AccessibilityMetrics, optional)
  - `fallback_used` (boolean)
  - `determinism_key` (string, derived from location id + destination list + config + network snapshot)

## Relationships

- `CanonicalLocation` -> `Coordinates` (1:1)
- `Destination` -> `Coordinates` (1:1)
- `Coordinates` -> `TravelRoute` (0:N)
- `TravelRoute` -> `AccessibilityMetrics` (1:1 aggregated)
- `AccessibilityMetrics` -> `AccessibilityOutcome` (1:1)

## State Transitions

1. **Resolved**: Coordinates resolved for property and destinations.
   - If property resolution fails -> `coordinate_unresolved` outcome.
2. **Routed**: Routing service invoked for travel time (car mode).
   - If routing fails -> fallback to Euclidean.
3. **Aggregated**: AccessibilityMetrics computed with sentinel values for unreachable routes.
4. **Attached**: AccessibilityOutcome attached to property feature set.
