# Data Model: Ingest municipal census datasets

**Date**: 2026-03-11
**Spec**: `specs/018-census-ingest/spec.md`

## Overview

The model tracks census ingestion runs, raw artifacts, normalized census records, area links, computed indicators, QA outcomes, coverage metrics, and promotion status.

## Entities

### CensusIngestionRun

- `run_id` (string, required)
- `trigger_type` (enum: `manual`, `scheduled`)
- `started_at` (datetime, required)
- `completed_at` (datetime, optional)
- `status` (enum: `running`, `failed`, `succeeded`)
- `warnings` (array, optional)

### CensusArtifact

- `artifact_id` (string, required)
- `run_id` (string, required)
- `collection_year` (int, required)
- `geography_level` (string, required)
- `refresh_date` (date, optional)
- `file_format` (string, required)
- `expected_schema` (json, required)
- `download_status` (enum: `ok`, `failed`)

### CensusValidationResult

- `validation_id` (string, required)
- `artifact_id` (string, required)
- `schema_ok` (bool, required)
- `value_constraints_ok` (bool, required)
- `required_keys_ok` (bool, required)
- `errors` (array, optional)

### AreaLinkResult

- `link_id` (string, required)
- `run_id` (string, required)
- `geography_level` (string, required)
- `coverage_percent` (float, required)
- `missing_area_ids` (array, optional)
- `mapping_table_used` (bool, required)

### IndicatorResult

- `indicator_id` (string, required)
- `run_id` (string, required)
- `area_id` (string, required)
- `indicator_name` (string, required)
- `value` (number, required)
- `limited_accuracy` (bool, required)

### QaResult

- `qa_id` (string, required)
- `run_id` (string, required)
- `totals_within_bounds` (bool, required)
- `range_checks_ok` (bool, required)
- `coverage_ok` (bool, required)
- `errors` (array, optional)

### PromotionResult

- `promotion_id` (string, required)
- `run_id` (string, required)
- `status` (enum: `promoted`, `failed`)
- `error` (string, optional)

## Relationships

- `CensusIngestionRun` -> `CensusArtifact` (1..N)
- `CensusArtifact` -> `CensusValidationResult` (1:1)
- `CensusIngestionRun` -> `AreaLinkResult` (1..N)
- `CensusIngestionRun` -> `IndicatorResult` (1..N)
- `CensusIngestionRun` -> `QaResult` (1..1)
- `CensusIngestionRun` -> `PromotionResult` (1..1)

## Notes

- Suppressed values are represented with explicit null/sentinel handling and reflected in `IndicatorResult.limited_accuracy`.
- Coverage metrics gate promotion; promotion is atomic to preserve last known-good indicators.
