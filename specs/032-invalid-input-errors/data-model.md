# Data Model: Provide Clear Error Messages for Invalid Inputs

**Date**: 2026-03-11
**Spec**: `specs/032-invalid-input-errors/spec.md`

## Overview

The model captures validation errors with field-level details and correction hints.

## Entities

### ValidationErrorResponse

- `status` (int, required)
- `error_code` (string, required)
- `message` (string, required)
- `errors` (array of ValidationErrorItem, required)

### ValidationErrorItem

- `field` (string, required)
- `reason` (string, required)
- `correction` (string, required)
- `severity` (string, required)
- `redacted_value` (string, optional)

## Notes

- Error items are ordered by severity.
- Sensitive values are redacted or truncated in `redacted_value`.
