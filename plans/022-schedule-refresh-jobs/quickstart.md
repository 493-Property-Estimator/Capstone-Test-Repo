# Quickstart: Schedule open-data refresh jobs

**Date**: 2026-03-11
**Spec**: `specs/022-schedule-refresh-jobs/spec.md`

## Purpose

Validate scheduled refresh orchestration, QA gating, and partial success summaries.

## Prerequisites

- Scheduler configured with dataset refresh policies and dependencies.
- Ingestion pipelines available in non-interactive mode.

## Suggested Test Flow

1. Trigger a scheduled run; verify workflow run ID and per-step IDs are recorded.
2. Verify dependency ordering and QA gating before promotion.
3. Simulate QA failure and confirm production data is preserved.
4. Simulate partial success and verify final summary lists promoted, skipped, and failed datasets.
5. Simulate retry behavior and verify warnings appear in summary.

## Example Summary (Shape)

```json
{
  "run_id": "refresh-20260311-001",
  "status": "partial_success",
  "promoted": ["geospatial", "pois"],
  "skipped": ["census"],
  "failed": ["assessments"],
  "reasons": {
    "census": "upstream dependency failed",
    "assessments": "QA threshold exceeded"
  }
}
```
