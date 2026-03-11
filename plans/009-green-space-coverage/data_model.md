# Data Model: UC-09 Green Space Coverage

## Entities

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string)

### Geometry
- **Fields**:
  - `geometry_id` (string)
  - `geometry_type` (enum: `point`, `parcel`)

### AnalysisBuffer
- **Fields**:
  - `buffer_type` (enum: `radius`, `polygon`)
  - `buffer_size` (number)
  - `total_area` (number)

### GreenSpaceArea
- **Fields**:
  - `area` (number)
  - `coverage_percent` (number)
  - `category_counts` (map)

### DesirabilityIndicator
- **Fields**:
  - `indicator` (number)
  - `weighting_version` (string)
  - `used_default_weights` (boolean)

### GreenSpaceOutcome
- **Fields**:
  - `status` (enum: `success`, `geometry_unresolved`, `fallback_used`)
  - `green_space_area` (GreenSpaceArea, optional)
  - `desirability_indicator` (DesirabilityIndicator, optional)
  - `absence_marked` (boolean)
  - `fallback_used` (boolean)
  - `determinism_key` (string, derived from location id + buffer config + dataset snapshot + config)

## Relationships

- `CanonicalLocation` -> `Geometry` (1:1)
- `Geometry` -> `AnalysisBuffer` (1:1)
- `AnalysisBuffer` -> `GreenSpaceArea` (1:1)
- `GreenSpaceArea` -> `DesirabilityIndicator` (1:1)
- `DesirabilityIndicator` -> `GreenSpaceOutcome` (1:1)

## State Transitions

1. **Resolved**: Geometry resolved for canonical location.
   - If resolution fails -> `geometry_unresolved` outcome with absence_marked.
2. **Buffered**: Analysis buffer computed.
3. **Queried**: Green space polygons queried for public/shared categories.
4. **Computed**: Area and coverage computed.
5. **Scored**: Desirability derived (default weights if needed).
6. **Attached**: GreenSpaceOutcome attached to property feature set.
