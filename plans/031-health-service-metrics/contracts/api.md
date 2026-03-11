# API Contract: Provide Health Checks and Service Metrics

**Date**: 2026-03-11
**Spec**: `specs/031-health-service-metrics/spec.md`

## Endpoints

- `GET /health`
- `GET /metrics`

## Health Response

```json
{
  "status": "healthy|degraded|unhealthy",
  "dependencies": [
    {"name": "string", "status": "ok|degraded|down", "details": "string"}
  ]
}
```

## Metrics Response

```json
{
  "request_count": 0,
  "error_count": 0,
  "cache_hit_ratio": 0,
  "routing_fallback_usage": 0,
  "avg_latency_ms": 0,
  "valuation_time_ms": 0
}
```

## Notes

- Health must include open-data freshness checks.
- Metrics output must be aggregated and redact identifiers.
