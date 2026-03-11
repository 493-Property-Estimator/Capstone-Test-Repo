# Research: Cache Frequently Requested Computations

**Date**: 2026-03-11
**Spec**: `specs/029-cache-computations/spec.md`

## Goals

- Confirm caching scope (full estimates only).
- Define cache validity checks and normalization rules.
- Ensure safe fallback when cache fails or is corrupted.

## Findings

- Cache scope is limited to full estimate results.
- Cached results must be validated by TTL and dataset freshness.
- Non-cacheable parameters must bypass cache.
- Cache outages must not block estimate responses.

## Open Questions

- What TTL and dataset version identifiers are used for freshness checks?
- What parameters are considered non-cacheable (debug, experimental weights)?
- What cache eviction policy is configured?

## Decisions (initial)

- Normalize request signature using property ID, factor configuration, and weights.
- Log cache hits, misses, and invalidations.
- Recompute on stale or corrupted cache entries.
