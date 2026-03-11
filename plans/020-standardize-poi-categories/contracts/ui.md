# UI Contract: Standardize POI categories across sources

**Date**: 2026-03-11
**Spec**: `specs/020-standardize-poi-categories/spec.md`

## Views

### POI Standardization Dashboard

Required elements:
- Run list with status, trigger type, taxonomy/mapping versions, and timestamps.
- Mapping quality metrics per run (mapped, unmapped, conflicts).
- Warnings for unmapped thresholds and conflicts blocking promotion.

### Run Detail View

- Provenance: taxonomy version, mapping version, source list.
- Mapping quality details: conflicting labels, unmapped labels with counts.
- Precedence rule outcomes when multiple raw fields exist.
- Promotion status and rollback outcomes.

## Copy Requirements

- Use consistent labels: "POI standardization", "Mapping quality", "Conflicts", "Promotion".
- Failure states must clarify production standardized categories remain unchanged.
