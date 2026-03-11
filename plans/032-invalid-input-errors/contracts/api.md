# API Contract: Provide Clear Error Messages for Invalid Inputs

**Date**: 2026-03-11
**Spec**: `specs/032-invalid-input-errors/spec.md`

## Error Response

```json
{
  "status": 400,
  "error_code": "string",
  "message": "string",
  "errors": [
    {"field": "string", "reason": "string", "correction": "string"}
  ]
}
```

## Notes

- Use HTTP 400 for unsupported formats and generic validation errors.
- Use HTTP 422 for semantically invalid inputs.
- Errors must be ordered by severity and redact sensitive values.
