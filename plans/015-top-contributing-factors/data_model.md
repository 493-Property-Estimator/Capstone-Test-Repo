# Data Model: UC-15 Top Contributing Factors

## Entities

### ExplanationRequest
- **Fields**:
  - `estimate_id` (string)
  - `top_n` (integer)

### FactorContribution
- **Fields**:
  - `factor_key` (string)
  - `label` (string)
  - `measured_value` (string)
  - `impact_direction` (enum: `increase`, `decrease`)
  - `impact_magnitude` (number, optional)
  - `impact_format` (enum: `currency`, `normalized`)
  - `has_map_context` (boolean)

### ExplanationResult
- **Fields**:
  - `increases` (list of FactorContribution)
  - `decreases` (list of FactorContribution)
  - `qualitative` (boolean)
  - `missing_categories` (list of strings)
  - `policy_filtered` (boolean)
  - `completeness_note` (string, optional)
  - `determinism_key` (string, derived from estimate id + config + data versions)

### ExplanationOutcome
- **Fields**:
  - `status` (enum: `success`, `qualitative_only`, `unavailable`)
  - `result` (ExplanationResult, optional)
  - `error_message` (string, optional)

## Relationships

- `ExplanationRequest` -> `ExplanationOutcome` (1:1)
- `ExplanationOutcome` -> `ExplanationResult` (0:1)

## State Transitions

1. **Retrieved**: Feature values and baseline metadata loaded.
2. **Attributed**: Per-factor contributions computed.
   - If unsupported -> `qualitative_only`.
3. **Ranked**: Top-N increases and decreases selected.
4. **Filtered**: Policy filters applied and completeness note set if needed.
5. **Returned**: ExplanationOutcome returned with determinism key.
