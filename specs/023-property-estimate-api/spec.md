# Feature Specification: Provide Property Value Estimate API Endpoint

**Feature Branch**: `023-property-estimate-api`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-23.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-23-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-23-AT.md"

## Clarifications

### Session 2026-03-10

- Q: Which status code should the API use for validation failures, given UC-23 says HTTP 400 but the malformed polygon acceptance test expects HTTP 422? → A: Use HTTP 400 for generic payload validation errors and HTTP 422 for semantically invalid but well-formed inputs such as self-intersecting polygons.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Request a property estimate (Priority: P1)

As a developer or client application, I need to submit an authenticated property reference to the estimate endpoint and receive a final property value estimate with baseline value, factor adjustments, and confidence metadata.

**Why this priority**: This is the primary user goal of UC-23 and the core product behavior.

**Independent Test**: Can be fully tested by sending valid authenticated requests with address, coordinate, or polygon inputs and verifying the response contains the estimate, baseline, adjustments, confidence, and traceability metadata.

**Acceptance Scenarios**:

1. **Given** a client has valid credentials and a resolvable property reference, **When** it sends an authenticated estimate request, **Then** the system returns HTTP 200 with a baseline value, estimated value, adjustments, confidence or completeness indicators, and a correlation ID.
2. **Given** a valid request requires factor retrieval and distance calculations, **When** the estimate is computed, **Then** the valuation engine aggregates available factors and returns the final estimated price.
3. **Given** the same successful request is repeated, **When** a valid recent cache entry exists, **Then** the system returns a consistent result and records a cache hit.

---

### User Story 2 - Get usable results despite partial dependency loss (Priority: P2)

As a developer or client application, I need the endpoint to continue returning a usable estimate when optional data or routing is unavailable, while clearly flagging approximations and missing factors.

**Why this priority**: The use case explicitly requires returning a result even if some optional open-data sources are missing.

**Independent Test**: Can be fully tested by simulating optional dataset outages, routing failures, and cache outages and confirming the endpoint still returns HTTP 200 with warnings, reduced confidence, and partial-data indicators where appropriate.

**Acceptance Scenarios**:

1. **Given** an optional open-data source is unavailable, **When** the endpoint computes an estimate, **Then** it omits the unavailable factor, reduces confidence or completeness, and returns missing-factor warnings.
2. **Given** the routing provider fails or times out, **When** distance-based factors are needed, **Then** the system falls back to straight-line distances and flags the approximation in the response and observability data.
3. **Given** the cache service is unavailable, **When** the endpoint receives an estimate request, **Then** it computes the estimate without caching and logs the cache issue for operations.

---

### User Story 3 - Receive controlled failures for invalid or unsupported requests (Priority: P3)

As a developer or client application, I need authentication, authorization, validation, coverage, and timeout failures to return structured, actionable errors so I can correct the request or handle the failure predictably.

**Why this priority**: Stable error behavior is necessary for integrating the API safely.

**Independent Test**: Can be fully tested by sending unauthenticated, unauthorized, malformed, unresolvable, baseline-missing, and timeout-triggering requests and verifying the system returns the expected failure class with structured error details and trace IDs.

**Acceptance Scenarios**:

1. **Given** the caller is unauthenticated or lacks permission, **When** it calls the endpoint, **Then** the system rejects the request with the appropriate authentication or authorization error and does not continue processing.
2. **Given** the request payload or property reference is invalid or unresolvable, **When** the endpoint validates or geocodes it, **Then** the system returns structured validation or resolution guidance and no estimate.
3. **Given** the baseline value is unavailable or computation exceeds the time budget, **When** the endpoint cannot complete the estimate safely, **Then** it returns a controlled failure response with traceability metadata.

### Edge Cases

- The caller omits authentication credentials.
- The caller is authenticated but lacks permission to access the endpoint.
- The request payload is malformed, incomplete, or contains invalid coordinates or geometry.
- An address cannot be resolved or resolves ambiguously.
- Baseline tax assessment data is unavailable for the property region.
- The routing provider fails or times out during distance calculations.
- One or more optional open-data sources are unavailable.
- The cache service is unavailable, stale, or invalidated by TTL or dataset version change.
- The valuation engine exceeds its time budget.

## Requirements *(mandatory)*

### Summary / Goal

Provide a stable authenticated API endpoint that returns a computed property valuation derived from a baseline tax assessment value and surrounding factors, while handling partial data availability, caching, validation, and dependency failures predictably.

### Actors

- **Primary Actor**: Developer / Client Application
- **Secondary Actors**: API Gateway, Authentication Service, Location Resolver/Geocoder, Feature Store Database, Distance Computation Service, Valuation Engine, Caching Layer, Logging/Monitoring Service

### Preconditions

- Client application is registered and has valid API credentials.
- Caller has permission to access the estimate endpoint.
- System has access to baseline tax assessment values for the requested region OR a configured method to retrieve them.
- Feature Store and Valuation Engine are online and reachable.

### Triggers

- Client application sends an authenticated request to the Estimate API endpoint (e.g., `POST /estimate`).

### Main Flow

1. **Developer** configures their client application with API credentials and endpoint URL.
2. **Client Application** constructs an estimate request containing a property identifier (address, coordinates, geo-shape, or property ID).
3. **Client Application** optionally includes tuning parameters (weights/sliders) and desired factor outputs (e.g., include crime breakdown).
4. **Client Application** sends an authenticated request to the Estimate API endpoint.
5. **API Gateway** receives the request, applies rate limiting, validates request size, and forwards it.
6. **Authentication Service** validates credentials and confirms the caller has permission.
7. **Estimate API** validates request payload format (required fields, geometry validity, coordinate bounds).
8. **Estimate API** resolves the property reference into a canonical location using the Location Resolver.
9. **Estimate API** checks the cache for an existing recent estimate matching the request signature.
10. **Estimate API** retrieves baseline assessment value and available cached features from the Feature Store.
11. **Estimate API** identifies missing required/optional features and selects a strategy:
    - retrieve from database if available,
    - compute quickly if feasible (approx walkability/driveability),
    - compute distances (road + straight-line),
    - omit unavailable optional features.
12. **Distance Computation Service** calculates distances to schools, green spaces, stores, and work areas (road and straight-line).
13. **Valuation Engine** computes adjustment contributions from all available factors.
14. **Valuation Engine** aggregates factor impacts using configured statistical methods (mean/median) and produces final estimated price.
15. **Valuation Engine** generates a confidence/completeness score based on feature availability and data freshness.
16. **Estimate API** assembles the response including baseline value, adjustments, confidence score, and missing-data indicators.
17. **Estimate API** stores result in cache with TTL for future reuse.
18. **Estimate API** returns HTTP 200 success response to the client.
19. **Logging/Monitoring Service** records request metrics (latency, cache hit/miss, missing-data flags, error rate).

### Alternate Flows

- **12a**: Routing provider fails or times out
  - **12a1**: System falls back to straight-line distance for distance-based factors.
  - **12a2**: Response includes a warning that routing distances were approximated.
- **13a**: Some open data sources are unavailable (crime, parks dataset, school dataset, etc.)
  - **13a1**: Valuation Engine omits those factors.
  - **13a2**: Confidence score is reduced and missing factor list returned.
- **14a**: Cache service is unavailable
  - **14a1**: System continues without caching and computes estimate normally.
  - **14a2**: Warning logged for operations team.

### Exception / Error Flows

- **4a**: Request is unauthenticated or has invalid credentials
  - **4a1**: Authentication Service rejects request with HTTP 401 and an actionable error message.
  - **4a2**: System logs rejected request for security auditing.
- **6a**: Caller is authenticated but lacks permission
  - **6a1**: Estimate API returns HTTP 403 and indicates missing scope/role.
- **7a**: Request payload fails validation (missing fields, malformed geo-shape, invalid address structure)
  - **7a1**: Estimate API returns HTTP 400 with structured field-level errors and suggestions.
- **8a**: Address cannot be resolved / geocoding fails
  - **8a1**: Location Resolver returns "not found" or "ambiguous."
  - **8a2**: Estimate API returns HTTP 422 with message prompting user to provide more detail or coordinates.
- **10a**: Baseline tax assessment value not available
  - **10a1**: Estimate API returns HTTP 424/422 indicating estimate cannot be computed without baseline.
  - **10a2**: Response includes which region or dataset is missing.
- **18a**: Valuation Engine computation exceeds time budget
  - **18a1**: Estimate API returns HTTP 503 with correlation ID.
  - **18a2**: System logs timeout metrics for performance monitoring.

### Data Involved

- API credentials
- Endpoint URL
- Property identifier
- Tuning parameters
- Desired factor outputs
- Request payload
- Request size
- Canonical location
- Request signature
- Baseline assessment value
- Available cached features
- Required and optional features
- Road and straight-line distances
- Factor adjustment contributions
- Final estimated price
- Confidence or completeness score
- Missing-data indicators
- Cache entry and TTL
- Request metrics, including latency, cache hit or miss, missing-data flags, and error rate
- Correlation ID

### Functional Requirements

- **FR-01-001**: The system MUST require authenticated requests to the estimate endpoint and reject unauthenticated or invalid-credential requests with HTTP 401 and an actionable error message.
- **FR-01-002**: The system MUST log rejected unauthenticated or invalid-credential requests for security auditing.
- **FR-01-003**: The system MUST validate that an authenticated caller has permission to access the estimate endpoint and reject unauthorized callers with HTTP 403 indicating the missing scope or role.
- **FR-01-004**: The system MUST accept estimate requests containing a property identifier as an address, coordinates, geo-shape, or property ID.
- **FR-01-005**: The system MUST accept optional tuning parameters and desired factor outputs in the request.
- **FR-01-006**: The API gateway MUST apply rate limiting, validate request size, and forward accepted requests.
- **FR-01-007**: The estimate API MUST validate request payload format, including required fields, geometry validity, and coordinate bounds.
- **FR-01-008**: The system MUST return HTTP 400 with structured field-level validation errors and suggestions for generic payload validation failures such as missing fields or out-of-range coordinates.
- **FR-01-009**: The system MUST return HTTP 422 for semantically invalid but well-formed request inputs such as self-intersecting polygons, with actionable validation details and suggestions.
- **FR-01-010**: The system MUST resolve the property reference into a canonical location.
- **FR-01-011**: The system MUST return HTTP 422 with guidance to provide more detail or coordinates when the address cannot be resolved or is ambiguous.
- **FR-01-012**: The system MUST include candidate suggestions or equivalent disambiguation guidance when an address is ambiguous, consistent with the response contract.
- **FR-01-013**: The system MUST check for an existing recent cached estimate matching the request signature before recomputing.
- **FR-01-014**: The system MUST return a consistent cached result for repeated identical requests when the cached entry is still valid.
- **FR-01-015**: The system MUST recompute the estimate instead of returning a stale cache entry when TTL expiration or dataset version invalidates the cache.
- **FR-01-016**: The system MUST retrieve the baseline assessment value and available cached features from the feature store.
- **FR-01-017**: The system MUST fail the request when the baseline tax assessment value is unavailable and identify the missing region or dataset.
- **FR-01-018**: The system MUST identify missing required and optional features and select a strategy to retrieve, compute, approximate, or omit them based on availability.
- **FR-01-019**: The system MUST calculate distance-based factors using road and straight-line distances as available.
- **FR-01-020**: The system MUST fall back to straight-line distance when the routing provider fails or times out.
- **FR-01-021**: The system MUST include a warning or fallback flag when routing distances are approximated.
- **FR-01-022**: The valuation engine MUST compute adjustment contributions from all available factors.
- **FR-01-023**: The valuation engine MUST aggregate factor impacts using configured statistical methods and produce a final estimated price.
- **FR-01-024**: The valuation engine MUST generate a confidence or completeness score based on feature availability and data freshness.
- **FR-01-025**: The system MUST assemble a success response including the baseline value, adjustments, confidence score, and missing-data indicators.
- **FR-01-026**: The system MUST return HTTP 200 for successful estimate responses.
- **FR-01-027**: The system MUST continue to return an estimate when optional open-data sources are unavailable by omitting unavailable optional factors.
- **FR-01-028**: The system MUST reduce confidence or completeness and return a missing-factor list when optional open-data sources are unavailable.
- **FR-01-029**: The system MUST continue processing without caching when the cache service is unavailable and log a warning for operations.
- **FR-01-030**: The system MUST store successful estimate results in cache with a TTL for future reuse.
- **FR-01-031**: The system MUST include a correlation or trace ID in successful and failing responses for traceability.
- **FR-01-032**: The logging and monitoring service MUST record request metrics including latency, cache hit or miss, missing-data flags, and error rate.
- **FR-01-033**: The system MUST log or emit metrics for routing fallback usage.
- **FR-01-034**: The system MUST return structured error responses for authentication, authorization, validation, resolution, baseline, and timeout failures without exposing internal stack traces.
- **FR-01-035**: The system MUST return HTTP 503 when valuation computation exceeds the configured time budget.
- **FR-01-036**: The system MUST log timeout metrics when valuation computation exceeds the configured time budget.

### Non-Functional Requirements

- **NFR-001**: In acceptance testing, full-coverage successful estimate requests MUST complete within 200 ms for uncached requests.
- **NFR-002**: The service MUST return structured responses that preserve traceability and do not expose internal stack traces on failures.
- **NFR-003**: Observability data MUST be sufficient to trace request latency, cache behavior, missing-data conditions, fallback usage, and timeout behavior.

### Key Entities *(include if feature involves data)*

- **Estimate Request**: Authenticated request containing a property identifier and optional tuning or output parameters.
- **Canonical Location**: Normalized property reference produced by the location resolver for downstream valuation and caching.
- **Estimate Result**: Response containing baseline value, estimated value, factor adjustments, completeness or confidence indicators, warnings, and traceability metadata.
- **Cache Entry**: Stored estimate result keyed by request signature and bounded by TTL or dataset-version validity.
- **Feature Set**: Baseline and supporting valuation factors retrieved, computed, approximated, or omitted for a request.

### Assumptions

- This specification is limited to UC-23 flows and UC-23 acceptance-test checks.
- Scenario narrative content was used only to confirm terminology, not to introduce requirements beyond the use case and acceptance tests.
- Implementation constraints for this repository remain Python and vanilla HTML/CSS/JS.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of valid authenticated requests in supported coverage areas return an estimate response containing baseline value, estimated value, confidence or completeness information, and traceability metadata.
- **SC-002**: In acceptance testing, 100% of requests missing only optional open-data factors still return HTTP 200 with missing-factor or fallback indicators instead of hard failure.
- **SC-003**: In acceptance testing, 100% of unauthenticated, unauthorized, invalid, unresolvable, baseline-missing, and timeout-triggering requests return structured error responses with the expected failure class and no internal stack trace exposure.
- **SC-004**: In acceptance testing, repeated identical valid requests return a consistent cached result when cache entries are valid, and stale entries trigger recomputation after TTL expiry or dataset-version invalidation.

## Traceability

### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-UC23-001 | FR-01-001, FR-01-034 |
| AT-UC23-002 | FR-01-004, FR-01-016, FR-01-022, FR-01-023, FR-01-024, FR-01-025, FR-01-026, FR-01-030, FR-01-031, FR-01-032 |
| AT-UC23-003 | FR-01-004, FR-01-010, FR-01-016, FR-01-019, FR-01-023, FR-01-026 |
| AT-UC23-004 | FR-01-004, FR-01-007, FR-01-016, FR-01-023, FR-01-024, FR-01-026 |
| AT-UC23-005 | FR-01-007, FR-01-009, FR-01-034 |
| AT-UC23-006 | FR-01-010, FR-01-011, FR-01-034 |
| AT-UC23-007 | FR-01-011, FR-01-012, FR-01-034 |
| AT-UC23-008 | FR-01-018, FR-01-025, FR-01-027, FR-01-028 |
| AT-UC23-009 | FR-01-019, FR-01-020, FR-01-021, FR-01-033 |
| AT-UC23-010 | FR-01-016, FR-01-017, FR-01-034 |
| AT-UC23-011 | FR-01-013, FR-01-014, FR-01-032 |
| AT-UC23-012 | FR-01-013, FR-01-015, FR-01-030 |
| AT-UC23-013 | FR-01-031 |
| AT-UC23-014 | FR-01-031, FR-01-034, FR-01-035, FR-01-036 |

### Flow Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow 1 | FR-01-001 |
| Main Flow 2 | FR-01-004 |
| Main Flow 3 | FR-01-005 |
| Main Flow 4 | FR-01-001, FR-01-026 |
| Main Flow 5 | FR-01-006 |
| Main Flow 6 | FR-01-003 |
| Main Flow 7 | FR-01-007, FR-01-008, FR-01-009 |
| Main Flow 8 | FR-01-010 |
| Main Flow 9 | FR-01-013 |
| Main Flow 10 | FR-01-016 |
| Main Flow 11 | FR-01-018 |
| Main Flow 12 | FR-01-019 |
| Main Flow 13 | FR-01-022 |
| Main Flow 14 | FR-01-023 |
| Main Flow 15 | FR-01-024 |
| Main Flow 16 | FR-01-025, FR-01-031 |
| Main Flow 17 | FR-01-030 |
| Main Flow 18 | FR-01-026 |
| Main Flow 19 | FR-01-032 |
| Alternate Flow 12a | FR-01-020, FR-01-021, FR-01-033 |
| Alternate Flow 13a | FR-01-027, FR-01-028 |
| Alternate Flow 14a | FR-01-029 |
| Exception Flow 4a | FR-01-001, FR-01-002, FR-01-034 |
| Exception Flow 6a | FR-01-003, FR-01-034 |
| Exception Flow 7a | FR-01-007, FR-01-008, FR-01-009, FR-01-034 |
| Exception Flow 8a | FR-01-011, FR-01-012, FR-01-034 |
| Exception Flow 10a | FR-01-017, FR-01-034 |
| Exception Flow 18a | FR-01-031, FR-01-035, FR-01-036 |
