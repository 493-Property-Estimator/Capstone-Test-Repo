# UI Contract: Property Details Estimate

## Inputs
- UI accepts location input plus one or more property attributes: size, bedrooms, bathrooms.

## Results
- On success, display estimate, low/high range, and an indicator that user attributes were incorporated.
- When only some attributes are provided, display a partial-attributes indicator.
- When baseline/feature data is partially unavailable, display a reduced-accuracy warning.
- On validation failure, display actionable field errors and no estimate/range.
- On normalization failure, display error and no estimate/range.

## Accessibility
- Validation errors and indicators must be visible and accessible via keyboard navigation.
