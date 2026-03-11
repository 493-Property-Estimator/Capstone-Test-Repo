# API Contract: Provide Partial Results When Some Open Data is Unavailable

**Date**: 2026-03-11
**Spec**: `specs/028-partial-open-data-results/spec.md`

## Response (200 OK)

```json
{
  "baseline_value": 0,
  "estimated_value": 0,
  "missing_factors": ["string"],
  "warnings": ["string"],
  "confidence_score": 0,
  "completeness_score": 0,
  "reliability_status": "normal|low|not_reliable"
}
```

## Error Responses

- `424 Failed Dependency`: baseline missing or strict-mode required factor missing

```json
{
  "error_code": "string",
  "message": "string",
  "missing_required_datasets": ["string"]
}
```

## Notes

- Low reliability must still return HTTP 200 with a high-severity warning.
- Strict mode failures must list missing required datasets.
