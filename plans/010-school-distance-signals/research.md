# Research: UC-10 School Distance Signals Planning

## Decision: Omit school features when coordinates cannot be resolved
**Rationale**: Clarification requires omission with explicit absence marking on coordinate-resolution failure.
**Alternatives considered**: Neutral defaults (rejected).

## Decision: Include all schools and map into elementary/secondary groups
**Rationale**: Clarification requires inclusion of all schools and mapping into required metric groups.
**Alternatives considered**: Only elementary/secondary subsets (rejected).

## Decision: Euclidean fallback on routing failure
**Rationale**: Alternate flow 4a requires fallback to straight-line distance when routing fails.
**Alternatives considered**: Fail computation (rejected).
