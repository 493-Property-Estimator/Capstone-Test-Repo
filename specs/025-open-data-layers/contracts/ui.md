# UI Contract: Toggle Open-Data Layers in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/025-open-data-layers/spec.md`

## Views

### Layer Panel

Required elements:
- Labeled toggles for expected layers with default states.
- Per-layer loading indicators.
- Legend entries for enabled layers.

### Layer Rendering

- Overlays render on top of base map with distinguishable styles.
- Multiple layers can be enabled simultaneously.
- Out-of-coverage and unavailable states show warnings.
- Performance mode and zoom-limit messages are visible when triggered.

## Copy Requirements

- Use consistent labels: "Layers", "Legend", "Layer unavailable".
- Warnings must be explicit and non-blocking.
