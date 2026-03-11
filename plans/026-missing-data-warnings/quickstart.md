# Quickstart: Show Missing-Data Warnings in UI

**Date**: 2026-03-11
**Spec**: `specs/026-missing-data-warnings/spec.md`

## Purpose

Validate warning severity, confidence display, and dismissal behavior.

## Prerequisites

- Estimate UI renders confidence and warnings.
- Estimate API returns missing-data metadata.

## Suggested Test Flow

1. Load full-coverage estimate; verify no warnings and high confidence.
2. Load partial-data estimate; verify warning panel with missing factors.
3. Load low-confidence estimate; verify prominent warning and non-blocking UI.
4. Trigger routing fallback; verify approximation message.
5. Simulate malformed metadata; verify generic warning and no crash.

## Example Warning (Shape)

```json
{
  "severity": "standard",
  "message": "Crime data unavailable",
  "details": ["Missing crime dataset for region"]
}
```
