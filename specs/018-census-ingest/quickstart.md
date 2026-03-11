# Quickstart: Ingest municipal census datasets

**Date**: 2026-03-11
**Spec**: `specs/018-census-ingest/spec.md`

## Purpose

Validate census ingestion, indicator computation, and coverage gating.

## Prerequisites

- Configured census source URLs and expected schemas.
- Boundary/area mapping tables available in the database.

## Suggested Test Flow

1. Start a manual census ingestion run with valid artifacts.
2. Verify normalized census staging tables and computed indicators are produced.
3. Verify coverage checks pass and promotion to production occurs atomically.
4. Simulate suppressed values and confirm indicators are flagged as limited accuracy.
5. Simulate low coverage or linking failures and confirm promotion is blocked.

## Example Run Metadata (Shape)

```json
{
  "run_id": "census-run-20260311-001",
  "status": "succeeded",
  "coverage_percent": 98.4,
  "census_year": 2025,
  "warnings": ["suppressed_values_present"]
}
```
