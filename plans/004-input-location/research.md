# Research: UC-04 Normalization Planning

## Decision: Deterministic spatial-unit resolution order (parcel → predefined unit → grid)
**Rationale**: Clarification and FR-01-068 require resolving overlaps by most specific unit. Implement as a consistent resolution policy to keep IDs stable.
**Alternatives considered**: Distance-based tie-breaking only; manual overrides (rejected due to determinism requirement).

## Decision: Type-prefixed canonical ID based on resolved unit
**Rationale**: Clarification and FR-01-083 require type-prefixed IDs, enabling stable downstream handling and clear provenance.
**Alternatives considered**: Hash-only IDs without type (rejected due to clarity and traceability requirements).

## Decision: Grid-cell fallback when no parcel or primary unit found
**Rationale**: Clarification and FR-01-165 require grid-cell fallback rather than nearest parcel or failure.
**Alternatives considered**: Nearest parcel fallback; failing the normalization (rejected by spec).

## Decision: Deterministic conflict resolution for duplicate IDs
**Rationale**: Alternate flow 6a and FR-01-195/210 require stable, unique IDs when conflicts occur.
**Alternatives considered**: Random suffix; manual intervention (rejected due to determinism).
