# Data Model: Schedule open-data refresh jobs

**Date**: 2026-03-11
**Spec**: `specs/022-schedule-refresh-jobs/spec.md`

## Overview

The model tracks refresh policies, workflow runs, step runs, dataset version records, and final summaries to ensure safe scheduled refreshes.

## Entities

### RefreshPolicy

- `policy_id` (string, required)
- `dataset_type` (string, required)
- `cadence` (string, required)
- `time_window` (string, required)
- `dependencies` (array, optional)

### WorkflowRun

- `run_id` (string, required)
- `trigger_type` (enum: `scheduled`, `on_demand`)
- `started_at` (datetime, required)
- `completed_at` (datetime, optional)
- `status` (enum: `running`, `partial_success`, `failed`, `succeeded`)
- `warnings` (array, optional)

### StepRun

- `step_id` (string, required)
- `run_id` (string, required)
- `dataset_type` (string, required)
- `status` (enum: `running`, `skipped`, `failed`, `succeeded`)
- `retry_count` (int, required)
- `started_at` (datetime, required)
- `completed_at` (datetime, optional)
- `error` (string, optional)

### DatasetVersion

- `dataset_type` (string, required)
- `version_id` (string, required)
- `promoted_at` (datetime, required)
- `source_version` (string, optional)
- `provenance` (string, optional)

### WorkflowSummary

- `run_id` (string, required)
- `promoted_datasets` (array, required)
- `skipped_datasets` (array, required)
- `failed_datasets` (array, required)
- `reason_by_dataset` (map, required)

## Relationships

- `WorkflowRun` -> `StepRun` (1..N)
- `WorkflowRun` -> `WorkflowSummary` (1..1)
- `DatasetVersion` -> `WorkflowRun` (N..1)

## Notes

- Partial success is represented when some datasets are promoted while others fail or are skipped.
- Dependency failure chains are recorded in step errors or summary reasons.
