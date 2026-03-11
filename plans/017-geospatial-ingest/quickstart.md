# Quickstart: Ingest open geospatial datasets

**Date**: 2026-03-11
**Spec**: `specs/017-geospatial-ingest/spec.md`

## Purpose

Validate ingestion of roads, boundaries, and POIs with QA gating and atomic promotion.

## Prerequisites

- Configured source URLs and expected schemas.
- Spatial database with staging and production schemas.

## Suggested Test Flow

1. Start a manual ingestion run with valid datasets.
2. Verify staging tables are populated and QA checks pass.
3. Verify production tables are atomically promoted and metadata is recorded.
4. Simulate a schema mismatch or invalid geometry and confirm promotion is blocked.
5. Simulate a promotion failure and confirm production tables remain unchanged.

## Example Run Metadata (Shape)

```json
{
  "run_id": "run-20260311-001",
  "status": "succeeded",
  "datasets": [
    {"type": "roads", "row_count": 12345, "version": "2026-02", "qa": "pass"},
    {"type": "boundaries", "row_count": 321, "version": "2026-02", "qa": "pass"},
    {"type": "pois", "row_count": 6789, "version": "2026-02", "qa": "pass"}
  ],
  "warnings": []
}
```
