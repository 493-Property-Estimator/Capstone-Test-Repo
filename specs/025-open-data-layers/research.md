# Research: Toggle Open-Data Layers in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/025-open-data-layers/spec.md`

## Goals

- Define layer toggle behavior and request debouncing.
- Clarify progressive loading and performance fallback.
- Ensure outages and partial coverage are communicated.

## Findings

- Debouncing is required for rapid toggles and pan/zoom events.
- Large layers require progressive loading with a visible indicator.
- Outages must disable toggles and avoid broken overlays.
- Partial coverage must warn without hiding available data.

## Open Questions

- What tile or chunk size is used for progressive loading?
- What zoom levels are supported for each layer?
- What is the configured debounce interval?

## Decisions (initial)

- Track layer toggle states and last requested bounds.
- Use per-layer loading indicators and warnings.
- Hide fine-grained layers beyond supported zoom levels.
