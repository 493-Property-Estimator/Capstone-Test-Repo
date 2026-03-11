# Research: Provide Health Checks and Service Metrics

**Date**: 2026-03-11
**Spec**: `specs/031-health-service-metrics/spec.md`

## Goals

- Define health status classification and dependency checks.
- Clarify metrics exposure and redaction requirements.
- Ensure stability under polling and dependency failures.

## Findings

- Health statuses include Healthy, Degraded, Unhealthy.
- Routing down with fallback yields Degraded; feature store down yields Unhealthy.
- Metrics must exclude raw identifiers and PII.
- Excessive polling should be rate limited.

## Open Questions

- What polling limits are configured for `/health`?
- Which metrics collector backend is used (if any)?
- What freshness threshold defines stale open-data ingestion?

## Decisions (initial)

- Include dependency status breakdown in health response.
- Record cache hit ratio and fallback usage in metrics.
- Redact identifiers before emitting metrics.
