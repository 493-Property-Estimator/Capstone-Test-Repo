# Research: UC-08 Travel Accessibility Planning

## Decision: Travel time as primary routing metric (car mode)
**Rationale**: Clarification requires travel time as primary metric and car travel as default mode.
**Alternatives considered**: Distance-only or multi-mode default (rejected).

## Decision: Euclidean fallback on routing failure
**Rationale**: Alternate flow 4a requires fallback to straight-line distance when routing fails.
**Alternatives considered**: Fail the computation (rejected).

## Decision: Omit accessibility features when property coordinates unresolved
**Rationale**: Clarification and exception flow require omission of travel-based features when property coordinates cannot be resolved.
**Alternatives considered**: Neutral defaults (rejected).
