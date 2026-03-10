# UI Contract: Address Estimate Flow

## Entry Point
- Provide an "Estimate Property Value" action that opens the address entry flow (FR-01-001).

## Address Entry
- Single address input field with prompt text to enter a street address (FR-01-002, FR-01-003).
- Validation errors must mention missing components (street number and street name) and block submission (FR-01-005).

## Disambiguation
- If multiple matches are returned, show a list of candidate addresses with locality context.
- User must select a candidate before proceeding (Clarifications).

## Results
- On success, display numeric estimate and low/high range (FR-01-010).
- Display a missing-data warning when partial estimate returned (FR-01-014).

## Failure States
- If geocoding fails or no match is found, show an error message and allow re-entry (FR-01-012).
- When the use case ends in failure, show the reason and a next step; do not show any estimate (FR-01-013).
