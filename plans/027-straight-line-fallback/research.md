# Research: Fall Back to Straight-Line Distance When Routing Fails

**Date**: 2026-03-11
**Spec**: `specs/027-straight-line-fallback/spec.md`

## Goals

- Define fallback behavior and mixed-mode output rules.
- Clarify error handling for disabled fallback and invalid coordinates.
- Ensure logging and correlation IDs for traceability.

## Findings

- Straight-line fallback is used only when routing fails and fallback is enabled.
- Partial routing failures require mixed-mode indicators in responses.
- Disabled fallback must return HTTP 503 with correlation ID.
- Invalid coordinates must return HTTP 422 without computing distances.

## Open Questions

- What are the configured caps for unreasonable straight-line distances?
- What thresholds define "unreasonable" distance for capping?
- What confidence reduction rules apply for fallback usage?

## Decisions (initial)

- Include fallback reason and distance method in responses.
- Record routing failure cause and correlation ID in logs.
- Apply capping before excluding a factor as unreliable.
