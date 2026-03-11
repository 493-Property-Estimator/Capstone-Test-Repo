# Quickstart: Use assessment baseline

**Date**: 2026-03-11
**Spec**: `specs/016-assessment-baseline/spec.md`

## Purpose

Verify baseline-anchored estimates and warnings using a minimal request/response flow.

## Prerequisites

- Assessment baseline data available in the Assessment Data Store.
- Feature store returns surrounding-factor features for the target location.

## Suggested Test Flow

1. Submit an estimate request with a known parcel that has baseline data.
2. Confirm the response includes:
   - `baseline_value` and baseline provenance fields
   - `final_estimate` consistent with baseline + adjustments
   - `correlation_id` and timestamp
3. Test ambiguous match handling by providing a location near multiple parcels; verify deterministic selection and warning.
4. Test missing/stale baseline behavior per policy (fallback or explicit error with warning).
5. Test partial feature availability and guardrail caps; verify warnings are surfaced.

## Example Request Payload

```json
{
  "location": "123 Example St, Example City",
  "include_breakdown": true
}
```

## Example Response Shape (Success)

```json
{
  "final_estimate": 525000,
  "baseline": {
    "baseline_value": 500000,
    "assessment_year": 2025,
    "jurisdiction": "Example City",
    "source_dataset": "Municipal Assessment",
    "assessment_unit_id": "PARCEL-001"
  },
  "adjustments": [
    {"category": "amenities", "adjustment_value": 15000},
    {"category": "accessibility", "adjustment_value": 10000}
  ],
  "warnings": [
    {"code": "partial_features", "message": "Crime data unavailable"}
  ],
  "correlation_id": "req-abc123",
  "generated_at": "2026-03-11T12:00:00Z"
}
```
