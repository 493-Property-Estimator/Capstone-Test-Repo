# Research: UC-14 Low/High Range Planning

## Decision: Graceful degradation to point estimate when range unavailable
**Rationale**: Clarification requires returning point estimate with range-unavailable warning if range cannot be computed.
**Alternatives considered**: Fail request (rejected).

## Decision: Configurable interval level with matching UI/metadata
**Rationale**: Clarification requires interval level to be configurable and consistently surfaced.
**Alternatives considered**: Fixed interval (rejected).

## Decision: Guardrail for unreasonably wide ranges
**Rationale**: Clarification requires a maximum width limit and adjustments when exceeded.
**Alternatives considered**: Return wide range without adjustment (rejected).
