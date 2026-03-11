# API Contract: Show Missing-Data Warnings in UI

**Date**: 2026-03-11
**Spec**: `specs/026-missing-data-warnings/spec.md`

## Estimate Response Fields

```json
{
  "baseline_value": 0,
  "final_estimate": 0,
  "factor_breakdown": [],
  "confidence_score": 0,
  "confidence_label": "high|medium|low",
  "missing_factors": ["string"],
  "approximations": ["string"]
}
```

## Notes

- Missing factors and approximations drive UI warning severity.
- Confidence label should be present when available.
