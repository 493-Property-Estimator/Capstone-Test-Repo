# Data Model: Precompute Grid-Level Features

**Date**: 2026-03-11
**Spec**: `specs/030-precompute-grid-features/spec.md`

## Overview

The model captures grid cells, aggregated feature values, freshness metadata, and job status.

## Entities

### GridCell

- `cell_id` (string, required)
- `bounds` (object, required)
- `resolution` (string, required)

### GridFeatureRecord

- `cell_id` (string, required)
- `mean_property_value` (number, required)
- `median_property_value` (number, required)
- `store_density` (number, required)
- `store_type_distribution` (object, required)
- `walkability_proxy` (number, required)
- `green_space_density` (number, required)
- `crime_rate` (number, required)
- `crime_severity_index` (number, required)
- `school_proximity_distribution` (object, required)
- `dataset_versions` (array, required)
- `freshness_timestamp` (datetime, required)

### PrecomputeJob

- `job_id` (string, required)
- `status` (enum: `running`, `failed`, `succeeded`)
- `started_at` (datetime, required)
- `completed_at` (datetime, optional)
- `warnings` (array, optional)

## Notes

- Records are regenerated entirely when grid resolution changes.
- Outlier flags are stored alongside records when triggered.
