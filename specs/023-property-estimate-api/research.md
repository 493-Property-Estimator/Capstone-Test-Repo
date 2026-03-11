# Research: Provide Property Value Estimate API Endpoint

**Date**: 2026-03-11
**Spec**: `specs/023-property-estimate-api/spec.md`

## Goals

- Confirm validation rules and error codes (400 vs 422).
- Define fallback behavior for missing optional data and routing failures.
- Ensure caching, traceability, and performance constraints are clear.

## Findings

- HTTP 400 is used for generic validation errors; HTTP 422 is used for semantically invalid but well-formed inputs (e.g., self-intersecting polygons).
- Optional data outages must still yield a 200 response with missing-factor warnings.
- Routing failures fall back to straight-line distances with a warning.
- Cache failures must not block estimation and must be logged.

## Open Questions

- What cache TTL and invalidation rules apply by dataset version?
- What confidence/completeness scoring formula is used?
- What time budget threshold triggers HTTP 503?

## Decisions (initial)

- Always include correlation ID in success and error responses.
- Provide structured error bodies with actionable guidance.
- Record cache hit/miss and fallback usage in metrics.
