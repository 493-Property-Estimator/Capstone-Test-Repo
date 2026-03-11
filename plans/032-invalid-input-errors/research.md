# Research: Provide Clear Error Messages for Invalid Inputs

**Date**: 2026-03-11
**Spec**: `specs/032-invalid-input-errors/spec.md`

## Goals

- Define consistent error schema and field-level guidance.
- Clarify status code usage (400 vs 422).
- Ensure sensitive values are redacted.

## Findings

- 400 is used for unsupported formats or generic validation failures.
- 422 is used for semantically invalid inputs (invalid coordinates, unresolvable address, self-intersecting polygon).
- Responses must include all validation errors ordered by severity.
- Correction guidance must be field-level, not full payloads.

## Open Questions

- What severity ordering is used for error lists?
- What redaction rules apply to sensitive values?
- What supported formats list is exposed in errors?

## Decisions (initial)

- Use a consistent top-level error schema with an errors array.
- Include field, reason, and correction hint per error.
- Redact or truncate sensitive values in error details.
