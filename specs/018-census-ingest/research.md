# Research: Ingest municipal census datasets

**Date**: 2026-03-11
**Spec**: `specs/018-census-ingest/spec.md`

## Goals

- Define ingestion stages: download, validate, normalize, link, compute, QA, publish.
- Clarify coverage thresholds and suppression handling.
- Ensure safe failure behavior that preserves last known-good indicators.

## Findings

- Suppressed or rounded values must not be treated as zeros; indicators relying on them require "limited accuracy" flags.
- Linking census geographies to internal area keys drives coverage; low coverage must block publication.
- Promotion must be atomic and leave production unchanged on failures.
- Run metadata must include provenance, coverage metrics, QA outcomes, and promotion status.

## Open Questions

- What are the configured coverage thresholds per geography level?
- What indicator formulas are allowed and where are they configured?
- What tolerances apply for repeated-run consistency checks?

## Decisions (initial)

- Represent suppression explicitly with nulls/sentinels and flag indicators that depend on them.
- Store coverage metrics per run and per geography level.
- Use run IDs with per-run status summaries for auditability.
