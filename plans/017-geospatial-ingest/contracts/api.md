# API Contract: Ingest open geospatial datasets

**Date**: 2026-03-11
**Spec**: `specs/017-geospatial-ingest/spec.md`

## Endpoint

`POST /api/ingestion/geospatial`

## Request

```json
{
  "trigger": "manual|scheduled",
  "datasets": ["roads", "boundaries", "pois"]
}
```

## Response (202 Accepted)

```json
{
  "run_id": "string",
  "status": "running",
  "started_at": "ISO-8601 timestamp"
}
```

## Response (200 OK) - Run Status

```json
{
  "run_id": "string",
  "status": "succeeded|failed",
  "datasets": [
    {
      "type": "roads|boundaries|pois",
      "version": "string",
      "row_count": 0,
      "qa_status": "pass|fail",
      "promotion_status": "promoted|failed",
      "warnings": ["string"]
    }
  ],
  "errors": ["string"],
  "completed_at": "ISO-8601 timestamp"
}
```

## Error Responses

- `400 Bad Request`: invalid dataset list or trigger
- `503 Service Unavailable`: ingestion service unavailable

## Notes

- Failures must report actionable details and must not indicate promotion succeeded if it did not.
- Promotion failures keep production tables unchanged.
