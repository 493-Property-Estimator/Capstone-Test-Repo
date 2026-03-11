# Research: UC-11 Commute Accessibility Planning

## Decision: Omit commute features on coordinate-resolution failure
**Rationale**: Clarification requires omission with explicit absence marking when coordinates cannot be resolved.
**Alternatives considered**: Neutral defaults (rejected).

## Decision: Neutral accessibility output for empty targets
**Rationale**: Clarification requires neutral indicator, null metrics, and zero target count with logging.
**Alternatives considered**: Fail computation (rejected).

## Decision: Euclidean fallback on routing failure
**Rationale**: Alternate flow 4a requires fallback to straight-line distance when routing fails.
**Alternatives considered**: Fail computation (rejected).
