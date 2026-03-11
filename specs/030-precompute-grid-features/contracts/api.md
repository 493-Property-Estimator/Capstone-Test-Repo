# API Contract: Precompute Grid-Level Features

**Date**: 2026-03-11
**Spec**: `specs/030-precompute-grid-features/spec.md`

## Endpoint

`POST /api/jobs/precompute-grid`

## Response (200 OK)

```json
{
  "job_id": "string",
  "status": "succeeded|failed",
  "warnings": ["string"]
}
```

## Notes

- Job summaries include dataset versions and freshness metadata in the report.
