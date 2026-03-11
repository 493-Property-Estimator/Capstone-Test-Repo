# API Contract: Search by Address in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/024-address-map-search/spec.md`

## Endpoint

`GET /api/geocode/search?q=...`

## Response (200 OK)

```json
{
  "suggestions": [
    {"display_text": "string", "rank": 0, "confidence": "string"}
  ]
}
```

## Response (200 OK) - Full Resolve

```json
{
  "canonical_address": "string",
  "coordinates": {"lat": 0, "lng": 0},
  "coverage_status": "supported|unsupported",
  "candidates": [
    {"display_text": "string", "coordinates": {"lat": 0, "lng": 0}}
  ]
}
```

## Error Responses

- `400 Bad Request`: query too short or invalid
- `503 Service Unavailable`: geocoding unavailable

## Notes

- Ambiguous results must include candidates for user selection.
- Out-of-coverage results must set `coverage_status` accordingly.
