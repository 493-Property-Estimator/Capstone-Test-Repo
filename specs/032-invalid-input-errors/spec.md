# Feature Specification: Provide Clear Error Messages for Invalid Inputs

**Feature Branch**: `032-invalid-input-errors`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "You are generating a feature specification for ONE use case, treated as a feature. Feature source files: - Use Cases (source of truth): ./Use cases/UC-32.md - Scenario narrative (supporting detail only if referenced): ./Scenarios/UC-32-Scenarios.md - Acceptance tests (source of truth for verifiable behavior): ./Acceptance Tests/UC-32-AT.md"

## Clarifications

### Session 2026-03-10

- Q: Should validation error responses include a full corrected payload example or only field-level correction guidance? → A: Include only field-level correction examples or hints, not a full corrected payload.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive Structured Validation Errors (Priority: P1)

As a developer or client application, I want invalid estimate requests to return structured field-level validation errors so that I can diagnose and correct the request quickly.

**Why this priority**: Structured, actionable validation feedback is the primary value of the feature because it reduces trial-and-error during API integration.

**Independent Test**: Can be fully tested by sending invalid estimate payloads with missing fields, invalid coordinates, invalid polygons, and unsupported formats, then verifying the error response contains actionable field-level details and no estimate.

**Acceptance Scenarios**:

1. **Given** a request is missing multiple required fields, **When** it is sent to the Estimate API, **Then** the response returns `400` or `422` and lists all missing fields with guidance in a consistent errors array.
2. **Given** a request includes invalid latitude and longitude values, **When** it is sent to `POST /estimate`, **Then** the response returns `422` with specific field-level range errors and no estimate.
3. **Given** a request uses an unsupported property reference format, **When** it is sent to the Estimate API, **Then** the response returns `400` and lists supported formats.

---

### User Story 2 - Get Guidance for Specialized Invalid Inputs (Priority: P2)

As a developer or client application, I want specialized invalid inputs such as self-intersecting polygons or unresolvable addresses to return corrective guidance so that I can choose a workable correction path.

**Why this priority**: Specialized validation feedback reduces integration friction for more complex request types beyond basic required-field checks.

**Independent Test**: Can be fully tested by submitting a self-intersecting polygon and a syntactically valid but non-existent address, then verifying the response explains the issue and suggests correction.

**Acceptance Scenarios**:

1. **Given** a request contains a self-intersecting polygon, **When** it is validated, **Then** the response explains the geometry problem and suggests correction.
2. **Given** a request contains a syntactically valid but unresolvable address, **When** it is validated, **Then** the response returns `422` and suggests adding postal code or using coordinates.

---

### User Story 3 - Keep Error Responses Safe and Consistent (Priority: P3)

As a developer or client application, I want error responses to be safe and consistent across failure types so that integrations can rely on a stable schema without exposing sensitive values.

**Why this priority**: Consistency and redaction are necessary for safe automated handling of validation failures across clients and environments.

**Independent Test**: Can be fully tested by triggering several different validation failures and comparing the returned schema while verifying sensitive values are redacted or truncated per policy.

**Acceptance Scenarios**:

1. **Given** validation is triggered by several failure types, **When** the responses are compared, **Then** the top-level error schema and per-error structure remain consistent.
2. **Given** a request contains sensitive values, **When** validation fails, **Then** the response identifies the field without echoing the full sensitive value.

### Edge Cases

- If multiple validation errors occur, the API must return the full list of issues instead of failing on the first one, with response ordering by severity.
- If a geo-shape is self-intersecting, the API must explain polygon validity rules and suggest simplification or correction.
- If an address is syntactically valid but not resolvable, the API must return `422` and suggest using latitude/longitude.
- If the request contains sensitive information, the API must redact the sensitive value while still identifying the field that failed validation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-01-001**: The system MUST accept estimate requests that may contain invalid or incomplete payloads and parse the payload to identify the request type, including address, coordinates, geo-shape, or property ID.
- **FR-01-002**: The system MUST validate the request schema and required fields for the identified request type.
- **FR-01-003**: The system MUST detect validation failures including missing fields, malformed polygons, and invalid latitude or longitude ranges.
- **FR-01-004**: The system MUST construct an error response containing an HTTP status code of `400` or `422`, a list of invalid fields, an error reason per field, and a recommended correction example.
- **FR-01-004A**: Recommended correction content in the error response MUST be limited to field-level correction examples or hints and MUST NOT require a full corrected payload example.
- **FR-01-005**: The system MUST return the structured error response to the client when validation fails.
- **FR-01-006**: The system MUST return all validation issues in a single response when multiple validation errors occur instead of failing on the first error.
- **FR-01-007**: The system MUST include ordering by severity when multiple validation errors are returned.
- **FR-01-008**: The system MUST explain polygon validity rules and suggest simplification or correction when a geo-shape is self-intersecting.
- **FR-01-009**: The system MUST return HTTP `422` for syntactically valid but unresolvable addresses and suggest using latitude and longitude instead.
- **FR-01-010**: The system MUST redact sensitive values in error responses while still identifying the associated field.
- **FR-01-011**: The system MUST return HTTP `400` and list supported formats when the request format is unsupported.
- **FR-01-012**: The system MUST avoid computing or returning an estimate when validation fails.
- **FR-01-013**: The system MUST keep a consistent top-level error schema across different validation failures.
- **FR-01-014**: The system MUST keep a consistent structure for individual error items across different validation failures.
- **FR-01-015**: The system MUST avoid exposing stack traces or internal error details in validation error responses.

### Non-Functional Requirements

- **NFR-001**: Validation error responses MUST be clear and actionable enough to support rapid developer debugging and API integration.
- **NFR-002**: Validation error responses MUST be safe for client exposure and avoid leaking sensitive or internal details.
- **NFR-003**: Delivery of this feature MUST remain within the project implementation constraints of Python and vanilla HTML/CSS/JS.

### Key Entities *(include if feature involves data)*

- **Estimate Request Payload**: The incoming request body submitted to the Estimate API for validation.
- **Request Type**: The identified input format for a request, such as address, coordinates, geo-shape, or property ID.
- **Validation Error Response**: The structured error response returned when validation fails.
- **Invalid Field Entry**: A field-level validation result identifying the failing field, its reason, and correction guidance.
- **Sensitive Value**: Request content that may need redaction in an error response.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of invalid requests tested return a structured error response with field-level guidance and no estimate result.
- **SC-002**: 100% of invalid latitude and longitude requests return specific range errors for each invalid coordinate field.
- **SC-003**: 100% of tested validation failure types use the same top-level error schema and per-error structure.
- **SC-004**: 100% of validation error responses omit full sensitive values and internal error details.

## Summary / Goal

The goal of this feature is to return structured, actionable, and safe validation errors for invalid Estimate API requests so developers can correct requests quickly.

For this feature, correction guidance is limited to field-level examples or hints rather than full corrected payloads.

## Actors

- Primary actor: Developer / Client Application
- Secondary actors: Validation Schema Service; Logging/Monitoring

## Preconditions

- API has defined request schemas for supported property input formats.
- Validation rules exist for coordinates, geo-shapes, and address formats.
- Error response schema is standardized and documented.

## Triggers

- Developer submits an API request with invalid or incomplete parameters.

## Main Flow

1. **Developer** sends a request to `/estimate` with invalid or incomplete payload.
2. **Estimate API** parses the payload and identifies the request type (address, coordinates, geo-shape, property ID).
3. **Estimate API** validates the request schema and required fields.
4. **Estimate API** detects validation failures (e.g., missing city, malformed polygon, invalid latitude range).
5. **Estimate API** constructs an error response containing:
   - HTTP status code (400/422),
   - list of invalid fields,
   - error reason per field,
   - recommended correction example.
6. **Estimate API** returns the structured error response to the client.
7. **Developer** reads the response and corrects the request.
8. **Developer** resubmits corrected request successfully.

## Alternate Flows

### 4a: Multiple validation errors occur

- **4a1**: API returns a list of all issues instead of failing on first error.
- **4a2**: Response includes ordering by severity.

### 4b: Invalid geo-shape is self-intersecting

- **4b1**: API returns message explaining polygon validity rules.
- **4b2**: Response suggests simplification or correction.

### 4c: Address is syntactically valid but not resolvable

- **4c1**: API returns HTTP 422 "Unprocessable Entity".
- **4c2**: Response suggests using lat/long instead.

### 5a: Developer request contains sensitive information

- **5a1**: API does not echo sensitive values back in error response.
- **5a2**: Error response redacts data but still identifies the field.

## Exception / Error Flows

### 2a: Unsupported request format

- **2a1**: API returns HTTP 400 with message listing supported formats.

## Data Involved

- Invalid or incomplete payload
- Request type
- Request schema
- Required fields
- Invalid fields
- Error reason per field
- Recommended correction example
- HTTP status code
- Sensitive information
- Structured error response

## Traceability

### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
|---|---|
| AT-UC32-001 — Multi-error for Missing Fields | FR-01-002, FR-01-004, FR-01-005, FR-01-006, FR-01-007, FR-01-012 |
| AT-UC32-002 — Invalid Lat/Long Range Returns Clear Error | FR-01-003, FR-01-004, FR-01-005, FR-01-012, FR-01-014, FR-01-015 |
| AT-UC32-003 — Invalid Polygon Geometry | FR-01-003, FR-01-008 |
| AT-UC32-004 — Unsupported Format | FR-01-001, FR-01-011 |
| AT-UC32-005 — Unresolvable Address Uses 422 | FR-01-009 |
| AT-UC32-006 — Sensitive Value Redaction | FR-01-010 |
| AT-UC32-007 — Schema Consistency Across Failures | FR-01-013, FR-01-014 |

### Flow Steps / Sections to Functional Requirements

| Flow Step or Section | Related FRs |
|---|---|
| Main Flow 1-2 | FR-01-001 |
| Main Flow 3 | FR-01-002 |
| Main Flow 4 | FR-01-003 |
| Main Flow 5 | FR-01-004, FR-01-013, FR-01-014, FR-01-015 |
| Main Flow 6 | FR-01-005 |
| Main Flow 7-8 | FR-01-012 |
| Alternate Flow 4a | FR-01-006, FR-01-007 |
| Alternate Flow 4b | FR-01-008 |
| Alternate Flow 4c | FR-01-009 |
| Alternate Flow 5a | FR-01-010 |
| Exception Flow 2a | FR-01-011 |

## Assumptions

- The scenario narrative was not needed to derive requirements because the use case flow and acceptance tests were sufficient.
- The acceptance tests require consistent schema semantics across validation failures but do not require the spec to choose between specific documented error schema standards.
- The use case open issue on corrected payload examples is resolved for this feature as field-level correction examples or hints only.
