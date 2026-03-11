# Data Model: UC-05 Location-Only Estimate

## Entities

### LocationOnlyRequest
- **Fields**:
  - `input` (PropertyInput)
  - `has_additional_attributes` (boolean, must be false)

### PropertyInput
- **Fields**:
  - `input_type` (enum: `address`, `coordinates`, `map_click`)
  - `address` (string, optional)
  - `coordinates` (Coordinates, optional)

### Coordinates
- **Fields**:
  - `latitude` (float)
  - `longitude` (float)

### CanonicalLocation
- **Fields**:
  - `canonical_location_id` (string)

### BaselineAssessmentData
- **Fields**:
  - `assessed_value` (number)
  - `assessment_date` (date)

### LocationFeatures
- **Fields**:
  - `features` (map of feature_name -> value)

### FallbackAverages
- **Fields**:
  - `source` (enum: `grid`, `neighbourhood`)
  - `average_value` (number)
  - `used` (boolean)

### EstimateRange
- **Fields**:
  - `low` (number)
  - `high` (number)
  - `widening_rule_applied` (boolean)

### PropertyEstimate
- **Fields**:
  - `estimate` (number)
  - `range` (EstimateRange)
  - `location_only_indicator` (string)
  - `reduced_accuracy_warning` (string, optional)

### EstimateOutcome
- **Fields**:
  - `status` (enum: `success`, `normalization_error`, `insufficient_data`)
  - `estimate` (PropertyEstimate, optional)
  - `error_message` (string, optional)

## Relationships

- `LocationOnlyRequest` -> `CanonicalLocation` (1:1)
- `CanonicalLocation` -> `BaselineAssessmentData` (1:1)
- `CanonicalLocation` -> `LocationFeatures` (1:1)
- `CanonicalLocation` -> `FallbackAverages` (0:1)
- `PropertyEstimate` -> `EstimateOutcome` (1:1)

## State Transitions

1. **Submitted**: LocationOnlyRequest received.
2. **Normalized**: CanonicalLocation resolved.
   - If normalization fails -> `normalization_error`.
3. **Data Fetched**: BaselineAssessmentData and LocationFeatures retrieved.
   - If baseline missing -> attempt FallbackAverages.
4. **Estimated**: PropertyEstimate computed with widening rule.
   - If insufficient data -> `insufficient_data`.
5. **Returned**: EstimateOutcome returned to UI/API.
