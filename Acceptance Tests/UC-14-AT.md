# Acceptance Tests — UC-14: Return a low/high range

## Purpose
Verify that the system returns and displays a point estimate plus a low/high range, correctly communicates uncertainty, and degrades gracefully when a reliable range cannot be computed.

## References
* User Story: **US-14: Return a low/high range**
* Use Case: `Use Cases/UC-14.md`
* Scenario: `Scenarios/SC-UC-14.md`
* Related Use Case: `Use Cases/UC-13.md` (point estimate)

## Assumptions (minimal)
* The estimate capability can return a point estimate and a low/high range when range computation is enabled.
* The response includes minimal metadata describing the range (e.g., `range_type` and/or interval level), plus a timestamp.
* If range computation fails, the product either (a) degrades gracefully to point estimate only with a warning, or (b) fails the request; these tests assume graceful degradation unless explicitly configured otherwise.

## Test Data Setup
Define controlled locations and configurations for repeatable tests:
* **L1 (Normal)**: Location with baseline and full feature availability; range expected.
* **L2 (Partial features)**: Location where at least one feature source is unavailable/disabled; range may still be computable but should be flagged.
* **L3 (Insufficient data for range)**: Location (or forced configuration) where the engine cannot compute a reliable range (e.g., too many missing features).
* **L4 (Guardrail case)**: A controlled case that would produce an invalid or unstable range without guardrails (e.g., low > high, negative low, extremely wide).
* The configured interval level/type (e.g., 80%/90%/95% band) is known for the environment under test so the UI label and metadata can be verified.

## Acceptance Test Suite (Gherkin-style)

### AT-14-01 — Return point estimate + low/high range (happy path)
**Given** the user requests an estimate for **L1**  
**And** the system can produce a point estimate and range for **L1**  
**When** the estimate response is returned  
**Then** the response contains exactly one point estimate (`estimated_value`)  
**And** the response contains a low/high range (`low_estimate`, `high_estimate`)  
**And** `low_estimate` ≤ `estimated_value` ≤ `high_estimate`  
**And** the response includes `timestamp` and minimal range metadata (e.g., `range_type` / interval label).

### AT-14-02 — UI clearly labels the range as uncertainty (not a guarantee)
**Given** the user views an estimate result for **L1** with a returned range  
**When** the UI renders the valuation result  
**Then** the UI displays the point estimate and the low/high range near each other  
**And** the range is explicitly labeled as an estimate range/uncertainty band  
**And** the UI includes a brief disclaimer or help text indicating the range is not a guaranteed bound.

### AT-14-03 — Formatting: range values are currency-formatted and ordered correctly
**Given** an estimate result for **L1** includes `low_estimate` and `high_estimate`  
**When** the UI displays the range  
**Then** both bounds are formatted as local currency using the configured rounding rules  
**And** the UI displays the bounds in ascending order (low then high) consistently across views.

### AT-14-04 — Range computation unavailable returns point estimate only with warning (graceful degradation)
**Given** the user requests an estimate for **L3** where a reliable range cannot be computed  
**When** the system processes the request  
**Then** the response includes `estimated_value` (point estimate)  
**And** the response omits `low_estimate`/`high_estimate` **or** marks them as unavailable per API convention  
**And** the response includes a warning indicating the range is unavailable and why (e.g., insufficient data)  
**And** the UI displays the point estimate and a non-blocking notice that the range is unavailable.

### AT-14-05 — Internal range computation error does not hide the point estimate (if configured)
**Given** the user requests an estimate for **L1**  
**And** the valuation engine encounters an internal error while computing the range  
**When** the system returns a response  
**Then** the point estimate is still returned and displayed (if graceful degradation is configured)  
**And** the range is omitted or flagged as unavailable  
**And** the UI shows a user-friendly warning (“Range temporarily unavailable”) and provides a retry path.

### AT-14-06 — Guardrails prevent invalid ranges and are transparent
**Given** the user requests an estimate for **L4** that would produce an invalid/unstable range without guardrails  
**When** the system computes the range  
**Then** the returned range satisfies basic validity constraints:
* `low_estimate` ≤ `high_estimate`
* `low_estimate` is not negative
* range width respects configured limits (if any)
**And** if an adjustment/fallback was applied, the response includes a warning (e.g., “range adjusted”)  
**And** the UI surfaces the adjustment warning in a non-blocking manner.

### AT-14-07 — Partial feature availability flags reduced reliability
**Given** the user requests an estimate for **L2** where some feature sources are unavailable  
**When** the system returns the estimate  
**Then** the system returns:
* (a) point estimate + range with a reduced-reliability warning, **or**
* (b) point estimate only with a “range unavailable” warning (if the range cannot be computed)  
**And** the UI does not imply missing features are zero-valued.

### AT-14-08 — Repeatability: same input yields consistent range for fixed versions
**Given** the user requests an estimate for **L1** multiple times  
**And** dataset versions and model/range configuration are unchanged between runs  
**When** results are returned  
**Then** the point estimate and range are consistent across requests within configured rounding rules  
**And** any warnings (if present) are consistent for the same conditions.

### AT-14-09 — Range metadata is present and consistent with product configuration
**Given** the system is configured to use a specific range type/interval level  
**When** an estimate for **L1** returns a range  
**Then** the API response includes metadata that identifies the range type/level (as configured)  
**And** the UI label/help text matches that configuration (no conflicting interval claims).

## Non-Functional Acceptance Criteria (verifiable)
* **Performance**: Adding range computation does not exceed agreed latency targets under normal load (e.g., p95 ≤ 3.5s for locations with cached features).
* **Reliability**: Range computation failures degrade gracefully (point estimate still shown) when configured; warnings are explicit.
* **Clarity**: The UI communicates that the range represents uncertainty and is not a guaranteed bound; wording is consistent across screens.

