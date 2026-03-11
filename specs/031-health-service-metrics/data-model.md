# Data Model: Provide Health Checks and Service Metrics

**Date**: 2026-03-11
**Spec**: `specs/031-health-service-metrics/spec.md`

## Overview

The model captures health responses, dependency statuses, and aggregated metrics output.

## Entities

### HealthResponse

- `status` (enum: `healthy`, `degraded`, `unhealthy`)
- `dependencies` (array, required)
- `timestamp` (datetime, required)

### DependencyStatus

- `name` (string, required)
- `status` (enum: `ok`, `degraded`, `down`)
- `details` (string, optional)

### MetricsOutput

- `request_count` (int, required)
- `error_count` (int, required)
- `cache_hit_ratio` (float, required)
- `routing_fallback_usage` (float, required)
- `avg_latency_ms` (int, required)
- `valuation_time_ms` (int, required)

## Notes

- Metrics output must be aggregated and free of raw identifiers.
- Open-data freshness checks are reflected in dependency statuses.
