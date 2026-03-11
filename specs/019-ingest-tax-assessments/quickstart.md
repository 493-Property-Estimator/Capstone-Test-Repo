# Quickstart: Ingest property tax assessment data

**Date**: 2026-03-11
**Spec**: `specs/019-ingest-tax-assessments/spec.md`

## Purpose

Validate assessment ingestion, linking, QA thresholds, and atomic promotion.

## Prerequisites

- Configured assessment source URLs and expected schema.
- Canonical location identifiers and linking inputs available.

## Suggested Test Flow

1. Start a manual assessment ingestion run with valid dataset.
2. Verify normalized records and link outcomes are stored.
3. Verify QA metrics meet thresholds and promotion occurs atomically.
4. Simulate invalid records and confirm quarantining plus invalid-rate gating.
5. Simulate promotion failure and confirm production baseline remains unchanged.

## Example Run Metadata (Shape)

```json
{
  "run_id": "assess-run-20260311-001",
  "status": "succeeded",
  "assessment_year": 2025,
  "coverage_percent": 96.2,
  "warnings": ["ambiguous_links_present"]
}
```
