# Data Model: Show Missing-Data Warnings in UI

**Date**: 2026-03-11
**Spec**: `specs/026-missing-data-warnings/spec.md`

## Overview

The model captures estimate response metadata, warning states, and UI interactions for missing-data messaging.

## Entities

### EstimateMetadata

- `baseline_value` (number, required)
- `final_estimate` (number, required)
- `factor_breakdown` (array, required)
- `confidence_score` (float, required)
- `confidence_label` (string, optional)
- `missing_factors` (array, optional)
- `approximations` (array, optional)

### WarningState

- `severity` (enum: `minor`, `standard`, `high`)
- `message` (string, required)
- `details` (array, optional)
- `expanded` (bool, required)

### DismissalState

- `dismissed` (bool, required)
- `indicator_visible` (bool, required)

## Notes

- Severity is derived from missing-factor count, confidence, and fallback flags.
- Malformed metadata triggers a generic warning state.
