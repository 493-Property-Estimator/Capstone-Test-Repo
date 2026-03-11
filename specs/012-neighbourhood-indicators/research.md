# Research: UC-12 Neighbourhood Indicators Planning

## Decision: Omit indicators on coordinate-resolution failure
**Rationale**: Clarification requires omission with explicit absence marking when coordinates cannot be resolved.
**Alternatives considered**: Neutral defaults (rejected).

## Decision: Deterministic boundary resolution policy
**Rationale**: Clarification requires a configured deterministic policy when boundaries overlap or are ambiguous.
**Alternatives considered**: Random tie-breaks (rejected).

## Decision: Fallback values for missing datasets
**Rationale**: Alternate flow 4a requires fallback values and logging when statistical datasets are incomplete.
**Alternatives considered**: Fail computation (rejected).
