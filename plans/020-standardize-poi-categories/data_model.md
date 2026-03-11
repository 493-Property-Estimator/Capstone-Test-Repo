# Data Model: Standardize POI categories across sources

**Date**: 2026-03-11
**Spec**: `specs/020-standardize-poi-categories/spec.md`

## Overview

The model tracks POI standardization runs, raw category fields, canonical assignments, mapping metadata, quality metrics, and promotion status.

## Entities

### StandardizationRun

- `run_id` (string, required)
- `taxonomy_version` (string, required)
- `mapping_version` (string, required)
- `trigger_type` (enum: `manual`, `scheduled`)
- `started_at` (datetime, required)
- `completed_at` (datetime, optional)
- `status` (enum: `running`, `failed`, `succeeded`)
- `warnings` (array, optional)

### RawPoiRecord

- `poi_id` (string, required)
- `source_id` (string, required)
- `raw_category` (string, required)
- `raw_category_secondary` (string, optional)
- `raw_category_tertiary` (string, optional)
- `ingested_at` (datetime, required)

### StandardizedPoiRecord

- `poi_id` (string, required)
- `source_id` (string, required)
- `canonical_category` (string, required)
- `canonical_subcategory` (string, optional)
- `raw_category` (string, required)
- `raw_category_secondary` (string, optional)
- `mapping_rule_id` (string, required)
- `mapping_rationale` (string, required)
- `taxonomy_version` (string, required)
- `mapping_version` (string, required)

### MappingQualityMetrics

- `run_id` (string, required)
- `source_id` (string, required)
- `mapped_percent` (float, required)
- `unmapped_percent` (float, required)
- `conflict_count` (int, required)
- `conflicting_labels` (array, optional)
- `unmapped_labels` (array, optional)

### PromotionResult

- `promotion_id` (string, required)
- `run_id` (string, required)
- `status` (enum: `promoted`, `failed`)
- `error` (string, optional)

## Relationships

- `StandardizationRun` -> `MappingQualityMetrics` (1..N)
- `StandardizationRun` -> `StandardizedPoiRecord` (1..N)
- `StandardizationRun` -> `PromotionResult` (1..1)

## Notes

- Conflicts are tracked per source and must block promotion.
- Unmapped labels may be promoted with warnings only if governance allows.
