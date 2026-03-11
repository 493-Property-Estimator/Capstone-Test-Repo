# API Contract: Use assessment baseline

**Date**: 2026-03-11
**Spec**: `specs/016-assessment-baseline/spec.md`

## Endpoint

`POST /api/estimate`

## Request

```json
{
  "location": "string (required)",
  "include_breakdown": true,
  "request_id": "string (optional)"
}
```

## Response (200 OK)

```json
{
  "final_estimate": 0,
  "baseline": {
    "baseline_value": 0,
    "assessment_year": 0,
    "jurisdiction": "string",
    "source_dataset": "string",
    "assessment_unit_id": "string",
    "dataset_version": "string (optional)",
    "refresh_date": "YYYY-MM-DD (optional)"
  },
  "adjustments": [
    {
      "category": "string",
      "adjustment_value": 0,
      "weight_version": "string (optional)"
    }
  ],
  "warnings": [
    {
      "code": "ambiguous_match|fallback_used|baseline_stale|baseline_missing|partial_features|guardrail_applied",
      "message": "string",
      "details": {"key": "value"}
    }
  ],
  "correlation_id": "string",
  "generated_at": "ISO-8601 timestamp"
}
```

## Response (4xx/5xx)

- `400 Bad Request`: invalid or unmappable location
- `404 Not Found`: baseline missing and policy forbids fallback
- `503 Service Unavailable`: baseline store unavailable

Error responses include:

```json
{
  "error": "string",
  "code": "string",
  "correlation_id": "string",
  "warnings": [
    {"code": "baseline_missing", "message": "string"}
  ]
}
```

## Notes

- The response must keep baseline provenance fields stable across repeated requests when data and configuration are unchanged.
- `final_estimate` must equal `baseline_value + sum(adjustments)` within configured rounding rules when breakdown is provided.
