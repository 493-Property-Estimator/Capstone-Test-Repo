# Research: UC-03 Map-Click Estimate Planning

## Decision: Click-to-coordinate precision enforced at 5 decimal places
**Rationale**: Clarification requires 5-decimal precision. Normalize click coordinates before boundary and valuation logic to ensure consistent IDs and estimates.
**Alternatives considered**: Using full map coordinate precision (rejected due to spec requirement).

## Decision: Inclusive boundary check for map clicks
**Rationale**: Clarification states boundary is inclusive; clicks on the boundary are accepted.
**Alternatives considered**: Exclusive boundary checks (rejected).

## Decision: Parcel snapping for between-parcel clicks
**Rationale**: Clarification requires snapping to nearest parcel centroid. Dedicated snapping service keeps normalization deterministic and testable.
**Alternatives considered**: Reject between-parcel clicks; defer to valuation layer (rejected).

## Decision: Latest-click-wins concurrency policy
**Rationale**: Clarification requires ignoring prior clicks. Implement cancellation/ignore semantics for pending requests so only the latest click updates UI.
**Alternatives considered**: Queue all clicks; debounce without cancellation (rejected).
