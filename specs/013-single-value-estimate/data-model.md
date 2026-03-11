# Data Model: UC-13 Single Estimated Value

## Entities

### EstimateRequest
- **Fields**:
  - `location_input` (PropertyInput)
  - `attributes` (PropertyAttributes, optional)
  - `request_id` (string)

### PropertyInput
- **Fields**:
  - `input_type` (enum: `address`, `coordinates`, `map_click`)
  - `address` (string, optional)
  - `coordinates` (Coordinates, optional)

### Coordinates
- **Fields**:
  - `latitude` (float)
  - `longitude` (float)

### BaselineMetadata
- **Fields**:
  - `assessment_year` (string)
  - `source` (string)
  - `fallback_used` (boolean)

### FeatureCoverage
- **Fields**:
  - `missing_features` (list of strings)
  - `warning` (string, optional)

### EstimateResult
- **Fields**:
  - `estimated_value` (number)
  - `currency` (string)
  - `rounding_rule` (string)
  - `timestamp` (datetime)
  - `location_summary` (string)
  - `baseline_metadata` (BaselineMetadata, optional)
  - `warnings` (list of strings)
  - `request_id` (string)

### EstimateOutcome
- **Fields**:
  - `status` (enum: `success`, `validation_error`, `normalization_error`, `valuation_error`)
  - `result` (EstimateResult, optional)
  - `error_message` (string, optional)
  - `validation_errors` (list of strings, optional)

## Relationships

- `EstimateRequest` -> `EstimateOutcome` (1:1)
- `EstimateOutcome` -> `EstimateResult` (0:1)

## State Transitions

1. **Validated**: Input validated.
   - If invalid -> `validation_error`.
2. **Normalized**: Location normalized.
   - If fails -> `normalization_error`.
3. **Estimated**: Estimate computed (baseline + features).
   - If fails -> `valuation_error`.
4. **Returned**: Single estimate returned with metadata and warnings.
