# Quickstart: Fall Back to Straight-Line Distance When Routing Fails

**Date**: 2026-03-11
**Spec**: `specs/027-straight-line-fallback/spec.md`

## Purpose

Validate routing fallback, mixed-mode results, and controlled failures.

## Prerequisites

- Routing provider can be simulated for timeouts.
- Estimate API returns fallback indicators.

## Suggested Test Flow

1. Run a routing-healthy estimate; verify road distances and no fallback flag.
2. Simulate routing timeout with fallback enabled; verify straight-line distances and warnings.
3. Simulate partial routing failures; verify mixed-mode indicators.
4. Disable fallback and simulate routing failure; verify HTTP 503 with correlation ID.
5. Send invalid coordinates; verify HTTP 422 with no distances.

## Example Response (Shape)

```json
{
  "distance_mode": "straight_line",
  "fallback_used": true,
  "fallback_reason": "routing_timeout"
}
```
