# Data Model: UC-02 Coordinates-to-Estimate

## Entities

### CoordinateInput
- **Fields**:
  - `latitude` (number, required, 5 decimal places)
  - `longitude` (number, required, 5 decimal places)
- **Validation**:
  - Latitude within -90 to +90
  - Longitude within -180 to +180
  - Precision of 5 decimal places

### CoordinateValidationResult
- **Fields**:
  - `is_valid` (boolean)
  - `errors` (list of strings)
  - `message` (string)

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
  - `latitude` (float)
  - `longitude` (float)

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string, required, stable across identical coordinate inputs)
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
  - `status` (enum: `success`, `validation_error`, `boundary_error`, `partial_data`, `failure`)
  - `canonical_location_id` (string, optional)
  - `estimate` (PropertyEstimate, optional)
  - `error_message` (string, optional)
  - `next_step` (string, optional)

## Relationships

- `CoordinateInput` -> `CoordinateValidationResult` (1:1)
- `CoordinateInput` -> `BoundaryValidationResult` (1:1)
- `CoordinateInput` -> `ParcelSnapResult` (1:1)
- `ParcelSnapResult` -> `CanonicalLocation` (1:1)
- `CanonicalLocation` -> `PropertyEstimate` (1:1)
- `PropertyEstimate` -> `EstimateResponse` (1:1)

## State Transitions

1. **Submitted**: CoordinateInput received.
2. **Validated**: CoordinateValidationResult produced.
   - If invalid -> `validation_error` response (no boundary check).
3. **Boundary Check**: BoundaryValidationResult produced.
   - If out-of-boundary -> `boundary_error` response (no estimate).
4. **Snapped**: ParcelSnapResult created (if between parcels).
5. **Normalized**: CanonicalLocation created.
6. **Estimated**: PropertyEstimate computed.
   - If partial -> `partial_data` response with warning (FR-02-014).
7. **Displayed**: EstimateResponse returned to UI/API.
