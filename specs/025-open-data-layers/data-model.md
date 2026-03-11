# Data Model: Toggle Open-Data Layers in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/025-open-data-layers/spec.md`

## Overview

The model tracks layer toggles, map bounds, layer data responses, and UI state for overlays and warnings.

## Entities

### LayerToggle

- `layer_id` (string, required)
- `label` (string, required)
- `enabled` (bool, required)
- `loading` (bool, required)

### MapBounds

- `north` (float, required)
- `south` (float, required)
- `east` (float, required)
- `west` (float, required)
- `zoom` (number, required)

### LayerDataResponse

- `layer_id` (string, required)
- `features` (array, required)
- `coverage_status` (enum: `complete`, `partial`)
- `received_at` (datetime, required)

### LayerWarning

- `layer_id` (string, required)
- `type` (enum: `unavailable`, `partial`, `performance`, `zoom`)
- `message` (string, required)

## Notes

- Coverage status drives the incomplete-coverage warning state.
- Zoom-based warnings are triggered when beyond supported resolution.
