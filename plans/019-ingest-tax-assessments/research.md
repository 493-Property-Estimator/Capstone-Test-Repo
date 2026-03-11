# Research: Ingest property tax assessment data

**Date**: 2026-03-11
**Spec**: `specs/019-ingest-tax-assessments/spec.md`

## Goals

- Define ingestion stages: download, validate, normalize, link, QA, promote.
- Clarify quarantine and QA-threshold policies for invalid records.
- Ensure deterministic linking and duplicate resolution.

## Findings

- Invalid records are quarantined; promotion is blocked only if invalid rate exceeds threshold.
- Deterministic linking is required, with ambiguity flags for audit.
- Promotion must be atomic and preserve last known-good baseline on failures.
- Run metadata must capture linking coverage, QA outcomes, and duplicate resolution results.

## Open Questions

- What are the configured QA thresholds for invalid rates, ambiguity, and coverage drops?
- What is the canonical location strategy priority order for linking?
- What rounding rules apply for repeated-run consistency?

## Decisions (initial)

- Store quarantined record counts and reasons per run.
- Record link method and confidence for every retained record.
- Use atomic table swaps for promotion.
