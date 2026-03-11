# Quickstart: Provide Property Value Estimate API Endpoint

**Date**: 2026-03-11
**Spec**: `specs/023-property-estimate-api/spec.md`

## Purpose

Validate request validation, fallbacks, caching, and response structure.

## Prerequisites

- API credentials and permissions configured.
- Baseline assessment data available in feature store.

## Suggested Test Flow

1. Submit a valid authenticated estimate request and verify HTTP 200 with baseline, adjustments, confidence, and correlation ID.
2. Submit a malformed payload and verify HTTP 400 with field-level errors.
3. Submit a self-intersecting polygon and verify HTTP 422 with actionable guidance.
4. Simulate routing failure and verify straight-line fallback with warning.
5. Simulate cache outage and verify computation succeeds with cache warning.

## Example Response (Shape)

```json
{
  "final_estimate": 525000,
  "baseline_value": 500000,
  "adjustments": [
    {"category": "amenities", "value": 15000},
    {"category": "accessibility", "value": 10000}
  ],
  "confidence_score": 0.82,
  "warnings": ["routing_fallback"],
  "correlation_id": "req-abc123"
}
```
