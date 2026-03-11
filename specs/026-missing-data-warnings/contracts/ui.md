# UI Contract: Show Missing-Data Warnings in UI

**Date**: 2026-03-11
**Spec**: `specs/026-missing-data-warnings/spec.md`

## Views

### Warning Panel

Required elements:
- Confidence indicator with percentage and label (when available).
- Banner-style warning panel for standard partial-data cases.
- Expand/collapse details for missing or approximated factors.
- Persistent warning indicator after dismissal.

### Warning Variants

- High severity banner for very low confidence.
- Small non-blocking notice for minor missing factors.
- Explicit routing fallback messaging for straight-line approximations.
- Generic warning when metadata is incomplete.

## Copy Requirements

- Use consistent labels: "Confidence", "Missing data", "Approximation".
- Warnings must be clear and non-blocking.
