# Quickstart: Precompute Grid-Level Features

**Date**: 2026-03-11
**Spec**: `specs/030-precompute-grid-features/spec.md`

## Purpose

Validate job execution, aggregates, and failure handling.

## Prerequisites

- Feature store tables exist for grid aggregates.
- Source datasets accessible or snapshots available.

## Suggested Test Flow

1. Trigger precompute job; verify success metrics and output tables.
2. Inspect grid records for mean/median values and freshness timestamps.
3. Simulate source outage; verify snapshot or warning behavior.
4. Simulate corrupted inputs; verify quarantine for affected region.
5. Simulate write failure; verify retries and rollback.

## Example Record (Shape)

```json
{
  "cell_id": "grid-001",
  "mean_property_value": 450000,
  "median_property_value": 430000,
  "freshness_timestamp": "2026-03-11T12:00:00Z"
}
```
