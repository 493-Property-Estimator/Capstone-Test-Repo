# Data Model: UC-01 Address-to-Estimate

## Entities

### AddressInput
- **Fields**:
  - `raw_address` (string, required)
  - `street_number` (string, derived, required)
  - `street_name` (string, derived, required)
  - `unit` (string, optional)
  - `city` (string, optional)
  - `region` (string, optional)
  - `postal_code` (string, optional)
- **Validation**:
  - Must include `street_number` and `street_name` (FR-01-005)
  - Format validation occurs before geocoding (FR-01-004)

### AddressValidationResult
- **Fields**:
  - `is_valid` (boolean)
  - `missing_components` (list of strings, e.g., `street_number`, `street_name`)
  - `message` (string)

### GeocodeRequest
- **Fields**:
  - `address` (AddressInput)
  - `attempt` (integer, starts at 1)
  - `session_id` (string, optional)

### GeocodeCandidate
- **Fields**:
  - `provider_id` (string)
  - `formatted_address` (string)
  - `coordinates` (Coordinates)
  - `locality` (string, optional)

### GeocodeResponse
- **Fields**:
  - `status` (enum: `success`, `no_match`, `unavailable`, `ambiguous`)
  - `coordinates` (Coordinates, present on success)
  - `candidates` (list of GeocodeCandidate, present on ambiguous)
  - `error_message` (string, present on failure)

### Coordinates
- **Fields**:
  - `latitude` (float)
  - `longitude` (float)

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string, required, stable across identical addresses)
  - `coordinates` (Coordinates)
  - `source_provider_id` (string)

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
  - `status` (enum: `success`, `validation_error`, `geocode_error`, `partial_data`, `failure`)
  - `canonical_location_id` (string, optional)
  - `estimate` (PropertyEstimate, optional)
  - `error_message` (string, optional)
  - `next_step` (string, optional)

## Relationships

- `AddressInput` -> `AddressValidationResult` (1:1)
- `AddressInput` -> `GeocodeRequest` (1:1)
- `GeocodeResponse.success` -> `CanonicalLocation` (1:1)
- `CanonicalLocation` -> `PropertyEstimate` (1:1)
- `PropertyEstimate` -> `EstimateResponse` (1:1)

## State Transitions

1. **Submitted**: AddressInput received.
2. **Validated**: AddressValidationResult produced.
   - If invalid -> `validation_error` response (no geocode).
3. **Geocoding**: GeocodeRequest sent.
   - If `ambiguous` -> UI disambiguation; new request with chosen candidate.
   - If `no_match` or `unavailable` -> `geocode_error` response with retry allowed (max 3).
4. **Normalized**: CanonicalLocation created.
5. **Estimated**: PropertyEstimate computed.
   - If partial -> `partial_data` response with warning (FR-01-014).
6. **Displayed**: EstimateResponse returned to UI/API.
