# Data Model: UC-04 Normalization

## Entities

### PropertyInput
- **Fields**:
  - `input_type` (enum: `address`, `coordinates`, `map_click`)
  - `address` (string, optional)
  - `coordinates` (Coordinates, optional)

### Coordinates
- **Fields**:
  - `latitude` (float)
  - `longitude` (float)

### GeocodeResult
- **Fields**:
  - `status` (enum: `success`, `no_match`, `unavailable`)
  - `coordinates` (Coordinates, optional)
  - `error_message` (string, optional)

### BoundaryValidationResult
- **Fields**:
  - `is_in_boundary` (boolean)
  - `message` (string)

### SpatialUnit
- **Fields**:
  - `unit_type` (enum: `parcel`, `predefined_unit`, `grid_cell`)
  - `unit_id` (string)

### SpatialResolutionResult
- **Fields**:
  - `status` (enum: `resolved`, `fallback_grid`, `not_found`)
  - `resolved_unit` (SpatialUnit)
  - `resolution_rule` (string, e.g., `parcel>predefined_unit>grid_cell`)

### CanonicalLocationId
- **Fields**:
  - `canonical_id` (string, type-prefixed)
  - `unit_type` (enum: `parcel`, `predefined_unit`, `grid_cell`)
  - `source_unit_id` (string)
  - `conflict_resolved` (boolean)
  - `conflict_strategy` (string, optional)
  - `stability_key` (string, deterministic key for identical inputs)

### NormalizationOutcome
- **Fields**:
  - `status` (enum: `success`, `geocode_error`, `boundary_error`, `resolution_error`)
  - `canonical_location_id` (CanonicalLocationId, optional)
  - `error_message` (string, optional)
  - `forwarded_downstream` (boolean)

## Relationships

- `PropertyInput` -> `GeocodeResult` (1:1 when address)
- `Coordinates` -> `BoundaryValidationResult` (1:1)
- `Coordinates` -> `SpatialResolutionResult` (1:1)
- `SpatialResolutionResult` -> `CanonicalLocationId` (1:1)
- `CanonicalLocationId` -> `NormalizationOutcome` (1:1)

## State Transitions

1. **Received**: PropertyInput received.
2. **Geocoded**: GeocodeResult created (if address).
   - If geocode failure -> `geocode_error` outcome.
3. **Boundary Check**: BoundaryValidationResult created.
   - If out-of-boundary -> `boundary_error` outcome.
4. **Resolved**: SpatialResolutionResult created.
   - If no parcel found -> `fallback_grid` resolution.
5. **ID Generated**: CanonicalLocationId created with type prefix.
6. **Forwarded**: NormalizationOutcome success forwarded to downstream valuation.
