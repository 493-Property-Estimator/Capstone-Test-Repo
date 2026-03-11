# Data Model: Ingest property tax assessment data

**Date**: 2026-03-11
**Spec**: `specs/019-ingest-tax-assessments/spec.md`

## Overview

The model tracks assessment ingestion runs, raw and normalized records, linking outcomes, QA metrics, and promotion status to safely publish a new baseline.

## Entities

### AssessmentIngestionRun

- `run_id` (string, required)
- `trigger_type` (enum: `manual`, `scheduled`)
- `started_at` (datetime, required)
- `completed_at` (datetime, optional)
- `status` (enum: `running`, `failed`, `succeeded`)
- `warnings` (array, optional)

### AssessmentArtifact

- `artifact_id` (string, required)
- `run_id` (string, required)
- `assessment_year` (int, required)
- `publication_date` (date, optional)
- `coverage_notes` (string, optional)
- `license_note` (string, optional)
- `file_format` (string, required)
- `expected_schema` (json, required)
- `download_status` (enum: `ok`, `failed`)

### AssessmentRecord

- `record_id` (string, required)
- `run_id` (string, required)
- `assessment_value` (number, required)
- `property_identifier` (string, required)
- `address` (string, optional)
- `parcel_id` (string, optional)
- `location_geometry` (geometry, optional)
- `normalized` (bool, required)
- `invalid_reason` (string, optional)
- `quarantined` (bool, required)

### LinkResult

- `link_id` (string, required)
- `record_id` (string, required)
- `canonical_location_id` (string, optional)
- `link_method` (enum: `direct`, `spatial`, `unlinked`)
- `confidence` (float, optional)
- `ambiguous` (bool, required)
- `reason_code` (string, optional)

### QaMetrics

- `qa_id` (string, required)
- `run_id` (string, required)
- `coverage_percent` (float, required)
- `unlinked_percent` (float, required)
- `ambiguous_percent` (float, required)
- `duplicate_rate` (float, required)
- `outlier_count` (int, required)
- `invalid_rate` (float, required)
- `coverage_drop_percent` (float, optional)

### PromotionResult

- `promotion_id` (string, required)
- `run_id` (string, required)
- `status` (enum: `promoted`, `failed`)
- `error` (string, optional)

## Relationships

- `AssessmentIngestionRun` -> `AssessmentArtifact` (1..N)
- `AssessmentIngestionRun` -> `AssessmentRecord` (1..N)
- `AssessmentRecord` -> `LinkResult` (0..1)
- `AssessmentIngestionRun` -> `QaMetrics` (1..1)
- `AssessmentIngestionRun` -> `PromotionResult` (1..1)

## Notes

- Quarantined records are retained for audit and excluded from promotion if thresholds are exceeded.
- Duplicate resolution outcomes are recorded per run to ensure determinism and auditability.
