# Quickstart: Provide Health Checks and Service Metrics

**Date**: 2026-03-11
**Spec**: `specs/031-health-service-metrics/spec.md`

## Purpose

Validate health status classification and metrics output.

## Prerequisites

- Dependencies can be toggled to simulate down/degraded.
- Metrics collection enabled.

## Suggested Test Flow

1. Call `/health` with all dependencies healthy; verify Healthy status.
2. Simulate routing down with fallback; verify Degraded status.
3. Simulate feature store down; verify Unhealthy status.
4. Call `/metrics`; verify aggregated counters and latency metrics without PII.
5. Burst `/health` polling; verify rate limiting.

## Example Health Response (Shape)

```json
{
  "status": "degraded",
  "dependencies": [
    {"name": "routing", "status": "down"}
  ]
}
```
