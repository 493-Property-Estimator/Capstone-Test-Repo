# Research: Provide Partial Results When Some Open Data is Unavailable

**Date**: 2026-03-11
**Spec**: `specs/028-partial-open-data-results/spec.md`

## Goals

- Define partial-result rules and strict-mode behavior.
- Clarify HTTP codes for baseline missing and low-reliability outputs.
- Ensure timeout handling is bounded.

## Findings

- Partial results should return HTTP 200 with warning severity HIGH when reliability is low.
- Baseline missing must return HTTP 424.
- Strict mode requires required factors or returns HTTP 424 with missing list.
- Timeouts should retry once or use cached data before omission.

## Open Questions

- What is the minimum reliability threshold before high-severity warning?
- Which datasets are treated as critical vs optional by default?
- What caching TTL applies to last-known open data snapshots?

## Decisions (initial)

- Always include missing factors, warnings, and completeness in partial responses.
- Use explicit reliability status to differentiate low-confidence outputs.
- Maintain strict-mode flag in request and response metadata.
