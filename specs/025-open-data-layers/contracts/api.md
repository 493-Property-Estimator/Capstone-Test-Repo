# API Contract: Toggle Open-Data Layers in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/025-open-data-layers/spec.md`

## Endpoint

`GET /api/layers/{layer_id}?bbox=...&zoom=...`

## Response (200 OK)

```json
{
  "layer_id": "string",
  "features": [],
  "coverage_status": "complete|partial"
}
```

## Error Responses

- `400 Bad Request`: invalid layer or bbox
- `503 Service Unavailable`: layer data unavailable

## Notes

- Responses must support partial coverage and include coverage status.
- Layer availability failures should be surfaced to the UI.
