# Data Model: Cache Frequently Requested Computations

**Date**: 2026-03-11
**Spec**: `specs/029-cache-computations/spec.md`

## Overview

The model captures normalized request signatures, cache keys, cached estimates, and freshness metadata.

## Entities

### CanonicalRequestSignature

- `signature` (string, required)
- `property_id` (string, required)
- `factor_config` (object, required)
- `weights` (object, required)

### CacheKey

- `key` (string, required)
- `signature` (string, required)

### CachedEstimate

- `estimate_id` (string, required)
- `result_payload` (object, required)
- `ttl_expires_at` (datetime, required)
- `dataset_versions` (array, required)

### CacheTelemetry

- `request_id` (string, required)
- `cache_hit` (bool, required)
- `latency_ms` (int, required)

## Notes

- Stale entries are invalidated when TTL expires or dataset versions change.
- Non-cacheable requests bypass cache entirely.
