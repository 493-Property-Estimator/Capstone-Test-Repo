# UI Contract: Schedule open-data refresh jobs

**Date**: 2026-03-11
**Spec**: `specs/022-schedule-refresh-jobs/spec.md`

## Views

### Refresh Runs Dashboard

Required elements:
- Run list with status, trigger type, and timestamps.
- Per-step status with dataset versions and retry counts.
- Alerts for start failures, QA failures, promotion failures, missing secrets, and time-window overruns.

### Run Detail View

- Dependency order and step run identifiers.
- QA results and promotion outcomes per dataset.
- Final summary listing promoted, skipped, and failed datasets with reasons.

## Copy Requirements

- Use consistent labels: "Refresh run", "Step status", "Promotion", "Summary".
- Failure states must clarify production data remains unchanged for failed datasets.
