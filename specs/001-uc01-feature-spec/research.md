# Research: UC-01 Address-to-Estimate Planning

## Decision: Geocoding provider abstraction with configurable backend
**Rationale**: The spec requires a geocoding service but does not mandate a vendor. A provider-agnostic adapter keeps the implementation aligned with the vanilla stack while preserving future portability and testing isolation. It also supports the error modes required by the flows (no match, service unavailable).
**Alternatives considered**: Hard-coding a single vendor SDK; deferring geocoding to the frontend (rejected due to error-handling and traceability requirements).

## Decision: Canonical location ID derived from geocoding result with stability guarantees
**Rationale**: FR-01-015 requires stable canonical IDs for identical addresses. Normalizing from provider identifiers (place ID or canonicalized address+coordinate hash) provides deterministic IDs without storing new state.
**Alternatives considered**: Persisting a new canonical ID table; using raw coordinates as IDs (rejected due to stability and precision variance).

## Decision: Disambiguation on multiple geocoding matches via explicit user selection
**Rationale**: Clarifications require presenting a disambiguation list. The UI will present candidate formatted addresses with locality context, and the API will accept a selected match identifier to continue.
**Alternatives considered**: Auto-selecting the first match; rejecting ambiguous inputs outright (rejected because it conflicts with the clarification).

## Decision: Retry policy and attempt tracking as request-scoped state
**Rationale**: The spec caps repeated failed attempts at 3. Track attempts within the user session or client request context to avoid new persistent storage while still enforcing the limit.
**Alternatives considered**: Persisting attempts in a database; unlimited retries (rejected by clarification).

## Decision: Single API endpoint for address estimates with structured error responses
**Rationale**: UI and API are both in scope. A single endpoint that returns either estimate data or structured errors supports both UI and automated acceptance tests.
**Alternatives considered**: Multiple endpoints for validation/geocode/estimate stages (rejected as unnecessary for this use case).
