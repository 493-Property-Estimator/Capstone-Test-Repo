# Research: UC-02 Coordinates-to-Estimate Planning

## Decision: Coordinate validation uses explicit range + precision rules before boundary checks
**Rationale**: Spec requires latitude/longitude ranges and precision to 5 decimal places before any further processing. Validating early avoids unnecessary boundary or valuation calls.
**Alternatives considered**: Implicit validation during boundary lookup (rejected because it violates FR-02-004 and FR-02-005 sequencing).

## Decision: Boundary check as inclusive polygon test
**Rationale**: Clarification states boundary inclusion is inclusive. Implement boundary validation to accept on-boundary points.
**Alternatives considered**: Exclusive boundary checks (rejected due to clarification).

## Decision: Parcel snapping for between-parcel coordinates
**Rationale**: Clarification requires snapping to nearest parcel centroid when coordinates fall between parcels. Implement as a dedicated service to keep normalization deterministic.
**Alternatives considered**: Nearest-feature snapping in valuation service; rejecting between-parcel coordinates (rejected by clarification).

## Decision: Canonical location ID derived from snapped parcel centroid and coordinate normalization
**Rationale**: FR-02-015 requires stability for identical coordinate inputs. Using normalized coordinates or parcel identifiers yields stable IDs without new persistent storage.
**Alternatives considered**: Persisting canonical IDs; using raw floating inputs directly (rejected due to precision instability).
