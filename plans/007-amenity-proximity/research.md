# Research: UC-07 Amenity Proximity Planning

## Decision: Shared search radius for all amenity categories
**Rationale**: Clarification requires a single shared radius across categories.
**Alternatives considered**: Per-category radius (rejected).

## Decision: Routing-based distance by default with Euclidean fallback
**Rationale**: Clarification and FR-01-045/135 require routing-based distance by default and Euclidean when routing fails.
**Alternatives considered**: Always Euclidean; always routing without fallback (rejected).

## Decision: Omit desirability adjustment when coordinates cannot be resolved
**Rationale**: Clarification requires omission of desirability adjustment on coordinate-resolution failure.
**Alternatives considered**: Neutral default score (rejected).
