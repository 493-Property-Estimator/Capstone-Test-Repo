# Data Model: UC-03 Map-Click Estimate

## Entities

### ClickEvent
- **Fields**:
  - `click_id` (string)
  - `timestamp` (datetime)
  - `raw_coordinates` (Coordinates)

### ClickResolutionResult
- **Fields**:
  - `is_resolved` (boolean)
  - `error_message` (string, optional)

### BoundaryValidationResult
- **Fields**:
  - `is_in_boundary` (boolean)
  - `message` (string)

### ParcelSnapResult
- **Fields**:
  - `snapped` (boolean)
  - `parcel_id` (string, optional)
  - `centroid_coordinates` (Coordinates)

### Coordinates
- **Fields**:
  - `latitude` (float, 5 decimal places)
  - `longitude` (float, 5 decimal places)

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string, required, stable within tolerance)
  - `coordinates` (Coordinates)
  - `source_parcel_id` (string, optional)

### EstimateRange
- **Fields**:
  - `low` (number)
  - `high` (number)

### PropertyEstimate
- **Fields**:
  - `estimate` (number)
  - `range` (EstimateRange)
  - `is_partial` (boolean)
  - `missing_data_warning` (string, optional)

### EstimateResponse
- **Fields**:
  - `status` (enum: `success`, `resolution_error`, `boundary_error`, `partial_data`, `failure`)
  - `canonical_location_id` (string, optional)
  - `estimate` (PropertyEstimate, optional)
  - `error_message` (string, optional)
  - `next_step` (string, optional)

### ClickRequestState
- **Fields**:
  - `latest_click_id` (string)
  - `status` (enum: `pending`, `completed`, `canceled`)

## Relationships

- `ClickEvent` -> `ClickResolutionResult` (1:1)
- `ClickEvent` -> `BoundaryValidationResult` (1:1)
- `ClickEvent` -> `ParcelSnapResult` (1:1)
- `ParcelSnapResult` -> `CanonicalLocation` (1:1)
- `CanonicalLocation` -> `PropertyEstimate` (1:1)
- `PropertyEstimate` -> `EstimateResponse` (1:1)

## State Transitions

1. **Clicked**: ClickEvent received.
2. **Resolved**: ClickResolutionResult produced.
   - If unresolved -> `resolution_error` response (no estimate).
3. **Boundary Check**: BoundaryValidationResult produced.
   - If out-of-boundary -> `boundary_error` response (no estimate).
4. **Snapped**: ParcelSnapResult created (if between parcels).
5. **Normalized**: CanonicalLocation created.
6. **Estimated**: PropertyEstimate computed.
   - If partial -> `partial_data` response with warning (FR-03-013).
7. **Displayed**: EstimateResponse returned to UI/API.
8. **Canceled**: Prior ClickRequestState marked canceled when a newer click arrives.
