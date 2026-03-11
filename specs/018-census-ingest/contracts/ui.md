# UI Contract: Ingest municipal census datasets

**Date**: 2026-03-11
**Spec**: `specs/018-census-ingest/spec.md`

## Views

### Census Ingestion Dashboard

Required elements:
- Run list with status, trigger type, census year, and timestamps.
- Coverage metrics and QA status at a glance.
- Warnings for suppression, coverage gaps, and linking failures.

### Run Detail View

- Provenance: source metadata, geography level, refresh date.
- Validation results: schema, value constraints, required keys.
- Linking results: coverage percent and missing area IDs.
- Indicator computation results and limited accuracy flags.
- Promotion status and rollback outcomes.

## Copy Requirements

- Use consistent labels: "Census ingestion", "Coverage", "QA checks", "Promotion".
- Failure states must clarify production indicators remain unchanged.
