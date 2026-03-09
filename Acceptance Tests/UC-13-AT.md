# Acceptance Tests — UC-13: Return a single estimated value

## Purpose
Verify that the system returns and displays one clear estimated property value for a requested location, including correct request validation, robust fallbacks for missing data, and user-friendly error handling.

## References
* User Story: **US-13: Return a single estimated value**
* Use Case: `Use Cases/UC-13.md`
* Scenario: `Scenarios/SC-UC-13.md`

## Assumptions (minimal)
* The UI provides a way to submit an estimate request using an address search and/or map click.
* The backend exposes an “estimate” capability (API endpoint name is implementation-specific) that returns a single numeric estimated value with basic metadata (timestamp, location summary, baseline metadata when available).
* Currency/rounding rules are defined by product requirements (tests verify consistency with the configured rules).

## Test Data Setup
Define controlled locations/addresses for repeatable tests:
* **A1 / L1 (Normal)**: Address/location that normalizes cleanly and has an assessment baseline and full feature availability.
* **A2 / L2 (Ambiguous)**: An address string that produces multiple plausible matches (e.g., same street name in multiple areas).
* **A3 / L3 (Unresolvable)**: An address that cannot be geocoded/normalized.
* **L4 (No baseline)**: A location that normalizes but has no assessment record (or is forced to simulate missing baseline).
* **L5 (Partial features)**: A location where at least one open-data feature source is unavailable or intentionally disabled for the test.
* Dataset versions and baseline assessment year/source are known and recorded so “as of” metadata can be verified.

## Acceptance Test Suite (Gherkin-style)

### AT-13-01 — Return a single estimate for a valid address (happy path)
**Given** the user selects address **A1** corresponding to location **L1**  
**And** baseline assessment data and required feature services are available for **L1**  
**When** the user submits an estimate request  
**Then** the system returns exactly one `estimated_value` (a single numeric value in local currency)  
**And** the response includes a `timestamp` for when the estimate was produced  
**And** the response includes a location summary (normalized address and/or coordinates)  
**And** the response includes baseline metadata (assessment year/source) when available  
**And** the UI displays the single estimated value prominently (not a range and not multiple competing numbers).

### AT-13-02 — Optional attributes are accepted and do not prevent estimation
**Given** the user selects address **A1** for location **L1**  
**And** the user provides valid optional attributes (e.g., bedrooms, bathrooms, size if supported)  
**When** the user submits an estimate request  
**Then** the request is accepted  
**And** the system returns one `estimated_value`  
**And** the UI preserves the entered attributes after the estimate is shown (so the user can adjust and re-run).

### AT-13-03 — Request validation rejects invalid inputs with actionable errors
**Given** the user has not provided a usable location (empty address) **or** provides invalid coordinates (out of range)  
**Or** the user provides invalid numeric attributes (e.g., negative size)  
**When** the user submits an estimate request  
**Then** the system returns a structured validation error identifying the invalid field(s)  
**And** the UI highlights the invalid input(s) and does not display an estimated value  
**And** the user can correct the inputs and resubmit without losing all entered data.

### AT-13-04 — Ambiguous address prompts user to disambiguate
**Given** the user enters ambiguous address **A2**  
**When** the system attempts to normalize the address  
**Then** the UI presents multiple candidate matches (or another disambiguation method)  
**And** the system does not produce an estimate until the user selects a specific match or sets the location via map click.

### AT-13-05 — Unresolvable address returns a user-friendly failure state
**Given** the user enters unresolvable address **A3**  
**When** the user submits an estimate request  
**Then** the system returns an error indicating the location could not be found/normalized  
**And** the UI displays a clear message and provides a way to retry (edit address and resubmit or choose map click)  
**And** the UI does not display a stale or previous estimate as if it applies to **A3**.

### AT-13-06 — Missing baseline uses configured fallback and is flagged
**Given** the user requests an estimate for location **L4** with no assessment baseline available  
**And** the system has a configured baseline fallback policy  
**When** the user submits an estimate request  
**Then** the system returns one `estimated_value` (if fallback policy allows estimation)  
**And** the response includes a warning/flag indicating the baseline was missing and a fallback was used  
**And** the UI surfaces that warning in a non-blocking way (the estimate remains visible).

### AT-13-07 — Missing feature sources produces an estimate with a completeness warning
**Given** the user requests an estimate for location **L5** where one or more feature sources are unavailable or time out  
**When** the user submits an estimate request  
**Then** the system returns one `estimated_value` using available features (if supported)  
**And** the response includes a warning/flag describing missing feature coverage  
**And** the UI displays the warning without implying the missing features are zero-valued.

### AT-13-08 — Valuation engine failure returns no estimate and a retry path
**Given** the user requests an estimate for **L1**  
**And** the valuation engine fails (internal error)  
**When** the system processes the request  
**Then** the response indicates that the estimate could not be produced  
**And** the UI shows a user-friendly error state with a retry option  
**And** no `estimated_value` is displayed for the failed request.

### AT-13-09 — Formatting: estimate is consistently displayed as currency with configured rounding
**Given** an estimate is returned for **L1**  
**When** the UI displays the result  
**Then** the value is formatted as local currency (currency symbol and separators)  
**And** rounding is applied consistently according to the configured product rule (e.g., nearest dollar or nearest thousand)  
**And** the UI does not show conflicting formats for the same estimate across views.

### AT-13-10 — Repeatability: same input yields consistent single-value output for fixed data versions
**Given** the user submits the same estimate request for **L1** multiple times  
**And** dataset versions, baseline data, and model version are unchanged between runs  
**When** the system returns results  
**Then** the returned `estimated_value` is consistent across requests within the defined rounding rule  
**And** the location summary and baseline metadata remain consistent for the same input.

### AT-13-11 — API response contains request tracing information for support/debugging (if supported)
**Given** the user submits an estimate request for **L1**  
**When** the API returns a successful response  
**Then** the response includes a correlation/request identifier (e.g., `request_id`) **or** the system logs one that can be tied to the client session  
**And** the identifier can be used to locate server logs for the request.

## Non-Functional Acceptance Criteria (verifiable)
* **Performance**: Under normal load, producing a single-value estimate meets an agreed latency target (e.g., p95 ≤ 3s) for locations with cached/precomputed features.
* **Reliability**: Partial data failures (missing one feature source) degrade gracefully with warnings rather than causing full failure when fallback behavior is defined.
* **Transparency**: The UI displays at least an “as of” timestamp; baseline year/source is shown when available; warnings are explicit when fallbacks are used.

