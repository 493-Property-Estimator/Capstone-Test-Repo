# Research: UC-06 Property Details Estimate Planning

## Decision: Validate size as positive numeric; beds/baths as non-negative numeric
**Rationale**: FR-01-045 and FR-01-060 define the validation rules, and failure paths require actionable errors.
**Alternatives considered**: Allowing zero size; integer-only constraints (rejected by spec).

## Decision: Partial attribute handling applies adjustments only for provided valid attributes
**Rationale**: Alternate flow 6a and FR-01-255/270 require supporting partial attributes while indicating partial incorporation.
**Alternatives considered**: Requiring complete attribute set; rejecting partial inputs (rejected).

## Decision: Range comparison rule for attribute-based vs location-only
**Rationale**: FR-01-120 and FR-01-315 require attribute-based ranges be equal to or narrower than location-only ranges for the same location.
**Alternatives considered**: Independent range computation without comparison (rejected).
