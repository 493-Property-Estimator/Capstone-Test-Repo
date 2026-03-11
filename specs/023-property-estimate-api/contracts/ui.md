# UI Contract: Provide Property Value Estimate API Endpoint

**Date**: 2026-03-11
**Spec**: `specs/023-property-estimate-api/spec.md`

## Views

### API Response Inspector (Dev Console)

Required elements:
- HTTP status and correlation ID.
- Baseline value, final estimate, adjustments, and confidence score.
- Missing-factor and fallback warnings.
- Structured error details for 400/401/403/422/424/503 responses.

## Copy Requirements

- Use consistent labels: "Estimate", "Baseline", "Adjustments", "Confidence", "Warnings".
- Error responses must include actionable guidance without exposing internals.
