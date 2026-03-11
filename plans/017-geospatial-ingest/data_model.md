# Data Model: Ingest open geospatial datasets

**Date**: 2026-03-11
**Spec**: `specs/017-geospatial-ingest/spec.md`

## Overview

The ingestion model tracks runs, datasets, staging/production tables, validation results, QA outcomes, and promotion status to ensure safe, traceable geospatial data ingestion.

## Entities

### IngestionRun

- `run_id` (string, required)
- `trigger_type` (enum: `manual`, `scheduled`)
- `started_at` (datetime, required)
- `completed_at` (datetime, optional)
- `status` (enum: `running`, `failed`, `succeeded`)
- `warnings` (array, optional)

### DatasetSource

- `source_id` (string, required)
- `name` (string, required)
- `dataset_type` (enum: `roads`, `boundaries`, `pois`)
- `publish_date` (date, optional)
- `version` (string, optional)
- `license_note` (string, optional)
- `file_format` (string, required)
- `expected_schema` (json, required)
- `url` (string, required)

### DatasetArtifact

- `artifact_id` (string, required)
- `source_id` (string, required)
- `run_id` (string, required)
- `checksum` (string, optional)
- `size_bytes` (int, required)
- `download_status` (enum: `ok`, `failed`)
- `download_error` (string, optional)

### ValidationResult

- `validation_id` (string, required)
- `artifact_id` (string, required)
- `schema_ok` (bool, required)
- `geometry_ok` (bool, required)
- `crs_ok` (bool, required)
- `repair_attempted` (bool, required)
- `repair_rate` (float, optional)
- `errors` (array, optional)

### QaResult

- `qa_id` (string, required)
- `run_id` (string, required)
- `dataset_type` (enum)
- `row_count` (int, required)
- `count_within_bounds` (bool, required)
- `spatial_sanity_ok` (bool, required)
- `duplicate_ids_found` (bool, required)
- `errors` (array, optional)

### PromotionResult

- `promotion_id` (string, required)
- `run_id` (string, required)
- `dataset_type` (enum)
- `status` (enum: `promoted`, `failed`)
- `error` (string, optional)

## Relationships

- `IngestionRun` -> `DatasetArtifact` (1..N)
- `DatasetArtifact` -> `ValidationResult` (1:1)
- `IngestionRun` -> `QaResult` (1..N)
- `IngestionRun` -> `PromotionResult` (1..N)

## Notes

- Run metadata must retain provenance and QA outcomes even for failed runs.
- Promotion swaps must be atomic to preserve last known-good production tables.
