# UI Contract: Location-Only Estimate

## Inputs
- UI accepts address, coordinate, or map-click input with no additional property attributes.

## Results
- On success, display estimate, low/high range, and location-only indicator.
- When fallback averages are used, display reduced-accuracy warning in addition to the location-only indicator.
- On normalization failure or insufficient data, display error and no estimate/range.

## Accessibility
- Location-only indicators and warnings must be visible and accessible via keyboard navigation.
