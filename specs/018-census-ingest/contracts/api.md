# API Contract: Ingest municipal census datasets

**Date**: 2026-03-11
**Spec**: `specs/018-census-ingest/spec.md`

## Endpoint

`POST /api/ingestion/census`

## Request

```json
{
  "trigger": "manual|scheduled",
  "geographies": ["neighbourhood", "tract", "block_group"]
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
  "census_year": 0,
  "coverage_percent": 0,
  "warnings": ["string"],
  "qa_status": "pass|fail",
  "promotion_status": "promoted|failed",
  "errors": ["string"],
  "completed_at": "ISO-8601 timestamp"
}
```

## Error Responses

- `400 Bad Request`: invalid geography list or trigger
- `503 Service Unavailable`: ingestion service unavailable

## Notes

- Failures must report actionable details and must not indicate promotion succeeded if it did not.
- Suppressed values must be flagged in warnings and downstream indicators marked limited accuracy.
