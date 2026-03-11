# Research: Schedule open-data refresh jobs

**Date**: 2026-03-11
**Spec**: `specs/022-schedule-refresh-jobs/spec.md`

## Goals

- Define scheduler orchestration requirements and dependency ordering.
- Clarify failure handling, retry/backoff, and alerting.
- Ensure final summaries reflect partial success accurately.

## Findings

- Runs must be non-interactive and dependency-ordered with per-step IDs.
- QA gating and atomic promotion are required per dataset.
- Failures must preserve last known-good production data and emit alerts.
- Final summaries must list promoted, skipped, and failed datasets with reasons.

## Open Questions

- What scheduler/orchestrator is used and how are time windows configured?
- What retry/backoff policy is configured for transient failures?
- What alert channels are required (email, Slack, dashboard)?

## Decisions (initial)

- Record workflow run IDs and per-step IDs for traceability.
- Publish partial successes with clear reporting and version records.
- Store run summaries with retry details and warnings.
