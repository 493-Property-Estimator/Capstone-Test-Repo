# API Contract: Provide Property Value Estimate API Endpoint

**Date**: 2026-03-11
**Spec**: `specs/023-property-estimate-api/spec.md`

## Endpoint

`POST /estimate`

## Request

```json
{
  "property": {
    "address": "string (optional)",
    "coordinates": {"lat": 0, "lng": 0},
    "polygon": "GeoJSON (optional)",
    "property_id": "string (optional)"
  },
  "tuning": {"weights": {}},
  "outputs": ["breakdown", "warnings"]
}
```

## Response (200 OK)

```json
{
  "final_estimate": 0,
  "baseline_value": 0,
  "adjustments": [{"category": "string", "value": 0}],
  "confidence_score": 0,
  "missing_factors": ["string"],
  "warnings": ["string"],
  "correlation_id": "string"
}
```

## Error Responses

- `400 Bad Request`: malformed payload, missing required fields, out-of-range coordinates
- `401 Unauthorized`: missing/invalid credentials
- `403 Forbidden`: missing scope or role
- `422 Unprocessable Entity`: semantically invalid geometry or unresolvable address
- `424 Failed Dependency`: baseline missing
- `503 Service Unavailable`: computation timeout

```json
{
  "error_code": "string",
  "message": "string",
  "details": {"field": "issue"},
  "correlation_id": "string"
}
```

## Notes

- HTTP 400 vs 422 must follow validation guidance in the spec.
- Responses must include a correlation ID for traceability.
