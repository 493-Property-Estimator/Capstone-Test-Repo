# API Contract: Schedule open-data refresh jobs

**Date**: 2026-03-11
**Spec**: `specs/022-schedule-refresh-jobs/spec.md`

## Endpoint

`POST /api/refresh/run`

## Request

```json
{
  "trigger": "scheduled|on_demand"
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
  "status": "succeeded|partial_success|failed",
  "step_runs": [
    {"dataset": "string", "status": "succeeded|failed|skipped", "retry_count": 0}
  ],
  "summary": {
    "promoted": ["string"],
    "skipped": ["string"],
    "failed": ["string"],
    "reasons": {"dataset": "reason"}
  },
  "warnings": ["string"],
  "errors": ["string"],
  "completed_at": "ISO-8601 timestamp"
}
```

## Error Responses

- `400 Bad Request`: invalid trigger
- `503 Service Unavailable`: scheduler unavailable

## Notes

- Missing secrets or QA failures must prevent promotion and be surfaced in summary.
- Runs must record workflow and step identifiers for traceability.
