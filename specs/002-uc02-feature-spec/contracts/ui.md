# UI Contract: Coordinate Estimate Flow

## Entry Point
- Provide an "Estimate Property Value" action that opens the coordinate entry flow (FR-02-001).

## Coordinate Entry
- Separate latitude and longitude input fields with prompts (FR-02-002, FR-02-003).
- Validation errors must indicate acceptable ranges and precision requirements (FR-02-004, FR-02-005).

## Results
- On success, display numeric estimate and low/high range (FR-02-012).
- Display a missing-data warning when partial estimate returned (FR-02-014).

## Failure States
- If coordinates are outside the supported area, show an error message and no estimate (FR-02-008).

## Accessibility
- Coordinate entry and error messaging must be operable via keyboard navigation and present accessible error text.
