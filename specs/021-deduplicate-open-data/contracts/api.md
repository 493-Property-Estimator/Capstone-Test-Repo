# API Contract: Deduplicate open-data entities

**Date**: 2026-03-11
**Spec**: `specs/021-deduplicate-open-data/spec.md`

## Endpoint

`POST /api/deduplication/run`

## Request

```json
{
  "trigger": "manual|scheduled",
  "entity_types": ["poi", "facility"]
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
  "count_reduction": 0,
  "review_candidates": 0,
  "rejected_candidates": 0,
  "qa_status": "pass|fail",
  "publication_status": "published|failed",
  "warnings": ["string"],
  "errors": ["string"],
  "completed_at": "ISO-8601 timestamp"
}
```

## Error Responses

- `400 Bad Request`: invalid entity types or trigger
- `503 Service Unavailable`: deduplication service unavailable

## Notes

- Publication must be atomic and must preserve last known-good canonical entities on failure.
- Low-confidence candidates must not be merged automatically.
