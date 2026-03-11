# Data Model: Provide Partial Results When Some Open Data is Unavailable

**Date**: 2026-03-11
**Spec**: `specs/028-partial-open-data-results/spec.md`

## Overview

The model captures estimate requests, dataset availability, partial-result metadata, and strict-mode requirements.

## Entities

### EstimateRequest

- `request_id` (string, required)
- `property_location` (object, required)
- `strict_mode` (bool, required)

### DatasetAvailability

- `dataset_name` (string, required)
- `status` (enum: `available`, `missing`, `timeout`)
- `used_cached` (bool, required)

### EstimateResult

- `baseline_value` (number, required)
- `estimated_value` (number, required)
- `missing_factors` (array, required)
- `confidence_score` (float, required)
- `completeness_score` (float, required)
- `reliability_status` (enum: `normal`, `low`, `not_reliable`)
- `warnings` (array, required)

### StrictModeFailure

- `missing_required_datasets` (array, required)
- `status_code` (int, required)

## Notes

- Reliability status drives warning severity.
- Strict mode failures return missing required datasets.
