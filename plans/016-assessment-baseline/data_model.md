# Data Model: Use assessment baseline

**Date**: 2026-03-11
**Spec**: `specs/016-assessment-baseline/spec.md`

## Overview

The model centers on an assessment baseline record that anchors each estimate. Estimates include factor adjustments, provenance, and warning flags for ambiguous matches, fallbacks, partial features, and guardrails.

## Entities

### AssessmentBaseline

- `baseline_id` (string, required)
- `assessment_unit_id` (string, required)
- `assessment_year` (int, required)
- `jurisdiction` (string, required)
- `source_dataset` (string, required)
- `baseline_value` (number, required)
- `dataset_version` (string, optional)
- `refresh_date` (date, optional)

### EstimateRequest

- `request_id` (string, optional)
- `location_input` (string, required)
- `normalized_location` (object, required)
- `lookup_key` (string, required)
- `timestamp` (datetime, required)

### FactorFeature

- `feature_id` (string, required)
- `category` (string, required)
- `value` (number | string, required)
- `availability_status` (enum: `available`, `missing`, `stale`)

### FactorAdjustment

- `feature_id` (string, required)
- `category` (string, required)
- `adjustment_value` (number, required)
- `weight_version` (string, optional)

### EstimateResult

- `estimate_id` (string, required)
- `baseline` (AssessmentBaseline, required)
- `adjustments` (array of FactorAdjustment, optional)
- `final_estimate` (number, required)
- `warnings` (array of WarningFlag, optional)
- `correlation_id` (string, required)
- `generated_at` (datetime, required)

### WarningFlag

- `code` (enum: `ambiguous_match`, `fallback_used`, `baseline_stale`, `baseline_missing`, `partial_features`, `guardrail_applied`)
- `message` (string, required)
- `details` (object, optional)

## Relationships

- `EstimateRequest` -> `AssessmentBaseline` (lookup by `lookup_key`)
- `EstimateResult` -> `AssessmentBaseline` (1:1)
- `EstimateResult` -> `FactorAdjustment` (0..N)
- `EstimateResult` -> `WarningFlag` (0..N)

## Notes

- Missing feature categories are captured via `FactorFeature.availability_status` and propagated to `WarningFlag`.
- Baseline provenance fields must remain stable across repeated requests when dataset versions and configuration are unchanged.
