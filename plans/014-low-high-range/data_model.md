# Data Model: UC-14 Low/High Range

## Entities

### PointEstimate
- **Fields**:
  - `estimated_value` (number)

### RangeEstimate
- **Fields**:
  - `low_estimate` (number)
  - `high_estimate` (number)
  - `range_type` (string)
  - `interval_level` (string)
  - `range_adjusted` (boolean)

### RangeWarnings
- **Fields**:
  - `range_unavailable` (boolean)
  - `range_adjusted` (boolean)
  - `reduced_reliability` (boolean)

### RangeResponse
- **Fields**:
  - `point` (PointEstimate)
  - `range` (RangeEstimate, optional)
  - `timestamp` (datetime)
  - `warnings` (RangeWarnings)

### RangeOutcome
- **Fields**:
  - `status` (enum: `success`, `range_unavailable`)
  - `response` (RangeResponse)

## Relationships

- `PointEstimate` -> `RangeResponse` (1:1)
- `RangeEstimate` -> `RangeResponse` (0:1)
- `RangeResponse` -> `RangeOutcome` (1:1)

## State Transitions

1. **Estimated**: Point estimate computed.
2. **Ranged**: Range computed and validated.
   - If range unavailable or invalid -> `range_unavailable` with warning.
3. **Returned**: RangeResponse returned with metadata and warnings.
