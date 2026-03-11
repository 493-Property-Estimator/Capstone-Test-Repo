# Quickstart: Cache Frequently Requested Computations

**Date**: 2026-03-11
**Spec**: `specs/029-cache-computations/spec.md`

## Purpose

Validate cache hits, misses, invalidation, and safe fallback behavior.

## Prerequisites

- Cache service configured and reachable.
- Dataset version metadata available.

## Suggested Test Flow

1. Submit an estimate request twice; verify second response is cached.
2. Expire TTL and verify recomputation and cache refresh.
3. Change dataset version and verify cache invalidation.
4. Simulate cache outage and verify recomputation succeeds.
5. Simulate corrupted cache entry and verify invalidation + recompute.

## Example Cache Record (Shape)

```json
{
  "signature": "abc123",
  "ttl_expires_at": "2026-03-11T12:00:00Z",
  "dataset_versions": ["crime:v2", "schools:v4"]
}
```
