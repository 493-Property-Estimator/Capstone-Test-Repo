# Quickstart: Standardize POI categories across sources

**Date**: 2026-03-11
**Spec**: `specs/020-standardize-poi-categories/spec.md`

## Purpose

Validate POI standardization, governance thresholds, and atomic promotion.

## Prerequisites

- Raw POIs ingested with source category fields.
- Canonical taxonomy and mapping rules available.

## Suggested Test Flow

1. Run standardization with full mappings; confirm canonical categories are assigned.
2. Verify mapping quality metrics (mapped/unmapped/conflicts) are reported.
3. Simulate new labels and confirm they are marked Unmapped/Other with counts.
4. Simulate conflicts and verify promotion is blocked.
5. Change taxonomy and rerun; verify reclassification without re-ingest.

## Example Run Metadata (Shape)

```json
{
  "run_id": "poi-std-20260311-001",
  "taxonomy_version": "v3",
  "mapping_version": "2026-03",
  "mapped_percent": 98.1,
  "unmapped_percent": 1.9,
  "conflict_count": 0
}
```
