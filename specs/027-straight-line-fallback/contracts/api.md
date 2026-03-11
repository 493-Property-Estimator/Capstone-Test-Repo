# API Contract: Fall Back to Straight-Line Distance When Routing Fails

**Date**: 2026-03-11
**Spec**: `specs/027-straight-line-fallback/spec.md`

## Response Fields

```json
{
  "distance_mode": "road|straight_line|mixed",
  "fallback_used": true,
  "fallback_reason": "string",
  "warnings": ["string"],
  "correlation_id": "string"
}
```

## Error Responses

- `422 Unprocessable Entity`: invalid or missing coordinates
- `503 Service Unavailable`: routing failure when fallback disabled

## Notes

- Mixed mode indicates road distance for some targets and fallback for others.
- Fallback responses must include warning indicators.
