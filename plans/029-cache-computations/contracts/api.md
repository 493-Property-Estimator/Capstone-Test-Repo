# API Contract: Cache Frequently Requested Computations

**Date**: 2026-03-11
**Spec**: `specs/029-cache-computations/spec.md`

## Response Metadata

```json
{
  "cache_hit": true,
  "cache_status": "hit|miss|stale|bypass",
  "correlation_id": "string"
}
```

## Notes

- Cache metadata should be included for observability.
- Cache bypass is used for non-cacheable requests.
