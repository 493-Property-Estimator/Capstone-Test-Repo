# UI Contract: Ingest open geospatial datasets

**Date**: 2026-03-11
**Spec**: `specs/017-geospatial-ingest/spec.md`

## Views

### Ingestion Run Dashboard

Required elements:
- Run list with status, start/end timestamps, and trigger type.
- Per-dataset status for roads, boundaries, and POIs.
- Download, validation, QA, and promotion stage summaries.
- Warnings and actionable error details.

### Run Detail View

- Source provenance: source name, publish date/version, license note, file format.
- Validation results: schema/geometry/CRS checks and repair outcomes.
- QA results: row counts, spatial sanity, duplicate IDs.
- Promotion status and rollback outcomes.

## Copy Requirements

- Use consistent labels: "Ingestion run", "Staging", "Promotion", "QA checks".
- Failure states must clarify that production data remains unchanged.
