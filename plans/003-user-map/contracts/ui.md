# UI Contract: Map Click Estimate Flow

## Map Interface
- Provide an interactive map with relevant layers (FR-03-001, FR-03-002).
- Capture clicks and show estimate results at or near the clicked location (FR-03-003, FR-03-011).

## Click Handling
- If click coordinates cannot be resolved, show an error and allow retry (FR-03-007).
- If click is outside supported boundary, show an error and no estimate (FR-03-006).
- For rapid repeated clicks, only the latest click result should render (FR-03-014).

## Results
- On success, display numeric estimate and low/high range (FR-03-011).
- Display a missing-data warning when partial estimate returned (FR-03-013).

## Accessibility
- Map interactions and error messaging must be operable via keyboard navigation and present accessible error text.
