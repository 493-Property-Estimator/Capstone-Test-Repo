# Data Model: UC-06 Property Details Estimate

## Entities

### PropertyDetailsRequest
- **Fields**:
  - `input` (PropertyInput)
  - `attributes` (PropertyAttributes)

### PropertyInput
- **Fields**:
  - `input_type` (enum: `address`, `coordinates`, `map_click`)
  - `address` (string, optional)
  - `coordinates` (Coordinates, optional)

### Coordinates
- **Fields**:
  - `latitude` (float)
  - `longitude` (float)

### PropertyAttributes
- **Fields**:
  - `size_sqft` (number, optional)
  - `bedrooms` (number, optional)
  - `bathrooms` (number, optional)

### AttributeValidationResult
- **Fields**:
  - `is_valid` (boolean)
  - `invalid_fields` (list of strings)
  - `message` (string)

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string)

### BaselineAssessmentData
- **Fields**:
  - `assessed_value` (number)

### LocationFeatures
- **Fields**:
  - `features` (map of feature_name -> value)

### EstimateRange
- **Fields**:
  - `low` (number)
  - `high` (number)
  - `narrower_than_location_only` (boolean)

### PropertyEstimate
- **Fields**:
  - `estimate` (number)
  - `range` (EstimateRange)
  - `attributes_incorporated` (list of strings)
  - `partial_attributes_indicator` (string, optional)
  - `reduced_accuracy_warning` (string, optional)

### EstimateOutcome
- **Fields**:
  - `status` (enum: `success`, `validation_error`, `normalization_error`)
  - `estimate` (PropertyEstimate, optional)
  - `error_message` (string, optional)

## Relationships

- `PropertyDetailsRequest` -> `AttributeValidationResult` (1:1)
- `PropertyDetailsRequest` -> `CanonicalLocation` (1:1)
- `CanonicalLocation` -> `BaselineAssessmentData` (1:1)
- `CanonicalLocation` -> `LocationFeatures` (1:1)
- `PropertyEstimate` -> `EstimateOutcome` (1:1)

## State Transitions

1. **Submitted**: PropertyDetailsRequest received.
2. **Validated**: AttributeValidationResult produced.
   - If invalid -> `validation_error`.
3. **Normalized**: CanonicalLocation resolved.
   - If normalization fails -> `normalization_error`.
4. **Estimated**: PropertyEstimate computed.
   - If partial data -> include reduced_accuracy_warning.
5. **Returned**: EstimateOutcome returned to UI/API.
