# Quickstart: Provide Clear Error Messages for Invalid Inputs

**Date**: 2026-03-11
**Spec**: `specs/032-invalid-input-errors/spec.md`

## Purpose

Validate structured validation errors and redaction.

## Prerequisites

- Validation rules configured for address, coordinates, polygon, and property ID.

## Suggested Test Flow

1. Send request with missing required fields; verify 400/422 and all missing fields listed.
2. Send invalid coordinates; verify 422 with field-level range errors.
3. Send self-intersecting polygon; verify 422 with correction guidance.
4. Send unsupported format; verify 400 with supported formats list.
5. Send unresolvable address; verify 422 with guidance to use lat/long.

## Example Error Response (Shape)

```json
{
  "status": 422,
  "error_code": "invalid_coordinates",
  "message": "Validation failed",
  "errors": [
    {"field": "coordinates.lat", "reason": "out of range", "correction": "use -90 to 90"}
  ]
}
```
