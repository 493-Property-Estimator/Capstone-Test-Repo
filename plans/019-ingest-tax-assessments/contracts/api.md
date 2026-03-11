# API Contract: Ingest property tax assessment data

**Date**: 2026-03-11
**Spec**: `specs/019-ingest-tax-assessments/spec.md`

## Endpoint

`POST /api/ingestion/assessments`

## Request

```json
{
  "trigger": "manual|scheduled",
  "assessment_year": 0
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
  "assessment_year": 0,
  "coverage_percent": 0,
  "invalid_rate": 0,
  "qa_status": "pass|fail",
  "promotion_status": "promoted|failed",
  "warnings": ["string"],
  "errors": ["string"],
  "completed_at": "ISO-8601 timestamp"
}
```

## Error Responses

- `400 Bad Request`: invalid assessment year or trigger
- `503 Service Unavailable`: ingestion service unavailable

## Notes

- Failures must report actionable details and must not indicate promotion succeeded if it did not.
- Invalid record handling must be visible via invalid-rate and warning fields.
