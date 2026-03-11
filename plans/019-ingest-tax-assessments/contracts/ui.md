# UI Contract: Ingest property tax assessment data

**Date**: 2026-03-11
**Spec**: `specs/019-ingest-tax-assessments/spec.md`

## Views

### Assessment Ingestion Dashboard

Required elements:
- Run list with status, trigger type, assessment year, and timestamps.
- Coverage, invalid-rate, and ambiguity metrics per run.
- Warnings for schema changes, linking ambiguity, QA threshold failures, and promotion failures.

### Run Detail View

- Provenance: assessment year, publication date, coverage notes, license/source.
- Validation results: schema, required fields, invalid values.
- Linking outcomes: linked/unlinked counts, ambiguous links, duplicate resolution summary.
- QA metrics and threshold outcomes.
- Promotion status and rollback outcomes.

## Copy Requirements

- Use consistent labels: "Assessment ingestion", "Coverage", "QA checks", "Promotion".
- Failure states must clarify production baseline remains unchanged.
