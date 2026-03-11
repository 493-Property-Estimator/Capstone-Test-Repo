# API Contract: Standardize POI categories across sources

**Date**: 2026-03-11
**Spec**: `specs/020-standardize-poi-categories/spec.md`

## Endpoint

`POST /api/standardization/poi-categories`

## Request

```json
{
  "trigger": "manual|scheduled",
  "taxonomy_version": "string",
  "mapping_version": "string"
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
  "taxonomy_version": "string",
  "mapping_version": "string",
  "mapped_percent": 0,
  "unmapped_percent": 0,
  "conflict_count": 0,
  "warnings": ["string"],
  "qa_status": "pass|fail",
  "promotion_status": "promoted|failed",
  "errors": ["string"],
  "completed_at": "ISO-8601 timestamp"
}
```

## Error Responses

- `400 Bad Request`: invalid taxonomy or mapping version
- `503 Service Unavailable`: standardization service unavailable

## Notes

- Conflicts must block promotion regardless of unmapped governance.
- Unmapped labels must be reported with counts by source.
