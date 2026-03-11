# Quickstart: Toggle Open-Data Layers in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/025-open-data-layers/spec.md`

## Purpose

Validate layer toggles, debounced fetches, and progressive loading.

## Prerequisites

- Map UI loads with layer panel.
- Layer Data API reachable for configured layers.

## Suggested Test Flow

1. Enable a layer and verify overlay + legend appear.
2. Pan/zoom map and verify layer updates with debounced requests.
3. Rapidly toggle a layer and verify final state is respected.
4. Enable a heavy layer and verify progressive rendering with a loading indicator.
5. Simulate API outage and verify "Layer unavailable" warning with toggle disabled.

## Example Layer Response (Shape)

```json
{
  "layer_id": "schools",
  "features": [],
  "coverage_status": "partial"
}
```
