# Research: Ingest open geospatial datasets

**Date**: 2026-03-11
**Spec**: `specs/017-geospatial-ingest/spec.md`

## Goals

- Define ingestion stages: download, validate, transform, QA, promote.
- Clarify failure behaviors to preserve last known-good data.
- Identify traceability requirements for run metadata.

## Findings

- Validation must cover schema, geometry validity, CRS, and required attributes.
- QA gates must block promotion on count anomalies, spatial sanity violations, and duplicates.
- Promotion must be atomic to avoid partial reads.
- Run metadata must capture provenance, versions, counts, warnings, QA outcomes, and promotion status.

## Open Questions

- What are the accepted CRS for each dataset and rules for missing CRS?
- What are expected count ranges per dataset for QA bounds?
- What tolerance thresholds apply for run-to-run consistency?

## Decisions (initial)

- Implement deterministic staging table names per run, then swap/rename for production.
- Use explicit failure states per dataset with actionable error details.
- Record run IDs and per-dataset metadata in a run report table.
