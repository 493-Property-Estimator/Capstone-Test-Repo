# Research: Show Missing-Data Warnings in UI

**Date**: 2026-03-11
**Spec**: `specs/026-missing-data-warnings/spec.md`

## Goals

- Define warning severity and UI presentation.
- Clarify confidence display and completeness summaries.
- Ensure graceful handling of malformed metadata.

## Findings

- Standard partial-data warnings use a banner-style warning panel.
- Confidence indicator should show both percentage and qualitative label when available.
- Very low confidence needs a prominent warning without blocking the estimate.
- Malformed metadata should show a generic warning and log the issue.

## Open Questions

- What thresholds define minor vs severe missing-factor warnings?
- What labels are used for qualitative confidence (e.g., high/medium/low)?
- What layout constraints exist for the warning panel?

## Decisions (initial)

- Use a collapsible warning panel with a persistent indicator on dismiss.
- Render missing-factor list with tooltips for impact explanations.
- Log malformed metadata and continue rendering estimates.
