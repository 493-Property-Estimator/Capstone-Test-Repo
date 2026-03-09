# Acceptance Test Suite — UC-23: Provide Property Value Estimate API Endpoint

## 1. Purpose
This acceptance test suite verifies that the Property Value Estimator platform provides a stable **Estimate API endpoint** that returns a final price estimate derived from a baseline tax assessment value adjusted by surrounding factors, and that the endpoint behaves correctly under missing data, fallback, caching, validation, and dependency failures.

## 2. Scope
In scope:
- Authenticated access to the estimate endpoint
- Input formats: address, coordinates, geo-shape, property ID
- Baseline assessment retrieval and use as valuation baseline
- Factor computation and aggregation (mean/median) where configured
- Confidence/completeness metadata and missing-factor reporting
- Routing fallback to straight-line distance
- Partial results behavior when optional open data is unavailable
- Caching behavior (hit/miss, TTL, staleness)
- Structured error responses and correlation IDs

Out of scope (unless specified elsewhere):
- Billing/quotas management
- Long-running asynchronous job orchestration
- UI rendering of results

## 3. Assumptions and Test Data
- A test client is provisioned with valid API credentials.
- Test regions exist with:
  - Full data coverage (baseline + comparables + routing + open datasets)
  - Partial coverage (some open datasets missing)
  - No baseline coverage (baseline absent)
- Sample property references:
  - `ADDR_FULL`: a resolvable address in full-coverage region
  - `ADDR_AMBIG`: an address that yields multiple candidates
  - `ADDR_NONE`: an address that cannot be resolved
  - `COORD_FULL`: valid lat/long in full-coverage region
  - `POLY_VALID`: valid polygon within supported bounds
  - `POLY_INVALID`: self-intersecting or malformed polygon
- Routing provider can be simulated to fail/timeout.
- Cache can be inspected (or metrics observed) to confirm hit/miss.

## 4. Entry and Exit Criteria
### Entry Criteria
- Estimate API deployed and reachable in test environment.
- Feature Store reachable and seeded with baseline assessment values for full/partial coverage regions.
- At least one known property in each coverage category exists.
- Ability to simulate dependency failures (routing down, dataset unavailable).

### Exit Criteria
- All Must/High priority tests pass.
- No Critical defects remain for UC-23 behaviors.

## 5. Test Environment
- API client (Postman/curl or automated test runner)
- API gateway + auth service enabled
- Feature Store + Valuation Engine deployed
- Routing service provider (or mock)
- Observability: logs + metrics accessible

---

## 6. Test Cases

### AT-UC23-001 — Endpoint Reachability
**Objective:** Verify the estimate endpoint is reachable and requires authentication.  
**Priority:** High

**Preconditions:**
- Estimate API base URL is known
- Client has network access

**Steps:**
1. Send an unauthenticated `POST /estimate` request with a minimal valid payload (e.g., COORD_FULL).

**Expected Results:**
- System responds with HTTP 401 (or equivalent) indicating authentication is required.
- Response body is structured and does not leak internal stack traces.

---

### AT-UC23-002 — Successful Estimate (Address Input)
**Objective:** Verify a full estimate is returned for a resolvable address in a full-coverage region.  
**Priority:** High

**Preconditions:**
- Valid credentials available
- Address "10234 98 Street NW, Edmonton, AB T5H 2P9" is resolvable
- Baseline assessment exists for this region

**Steps:**
1. Send authenticated `POST /estimate` with payload:
```json
{
  "address": {
    "street": "10234 98 Street NW",
    "city": "Edmonton",
    "province": "AB",
    "postalCode": "T5H 2P9"
  },
  "factorWeights": "default"
}
```
2. Record response payload and headers.

**Expected Results:**
- System returns HTTP 200.
- Response contains:
  - `baselineValue`: numeric (e.g., 425000)
  - `estimatedValue`: numeric (e.g., 455000)
  - `confidence`: percentage (e.g., 85)
  - `adjustments`: object with breakdown by factor (schools, parks, crime, stores, etc.)
  - `correlation_id`: present for tracing
- `completeness` field shows 100% (or close) for full-coverage region
- No missing-factor warnings present
- Response time < 200ms (with uncached computation)

**Postconditions:**
- Request logged with correlation ID
- Result cached for subsequent requests with same parameters

---

### AT-UC23-003 — Successful Estimate (Coordinate Input)
**Objective:** Verify estimate works with coordinate-only requests.  
**Priority:** High

**Preconditions:**
- Valid credentials available
- Coordinates (53.5461°N, -113.4938°W) are within Edmonton support area
- Baseline assessment retrievable for that location

**Steps:**
1. Send authenticated `POST /estimate` with payload:
```json
{
  "coordinates": {
    "lat": 53.5461,
    "lng": -113.4938
  }
}
```
2. Verify canonical location is returned.

**Expected Results:**
- HTTP 200 returned.
- Response includes:
  - `canonicalLocationId`: normalized identifier (e.g., "EDM-PAR-2847591")
  - `baselineValue`: numeric baseline value
  - `estimatedValue`: adjusted final estimate
  - `confidence`: 80-90% range expected
  - Factor breakdown with distances to amenities
- Response includes coordinates echoed back or resolved property address
- Total response time < 200ms

---

### AT-UC23-004 — Successful Estimate (Valid Polygon Input)
**Objective:** Verify estimate works with geo-shape polygon input within supported bounds.  
**Priority:** High

**Preconditions:**
- Valid credentials available
- POLY_VALID is within supported bounds
- Baseline assessment can be derived for polygon area

**Steps:**
1. Send authenticated `POST /estimate` with `POLY_VALID` payload.
2. If API supports aggregation over area, request an area-based estimate (per API contract).

**Expected Results:**
- HTTP 200 returned.
- Response includes final estimate and baseline used.
- Response indicates whether polygon was reduced to centroid or area-aggregated (per contract).
- Confidence/completeness is included.

---

### AT-UC23-005 — Validation Error: Malformed Polygon
**Objective:** Verify invalid geo-shape payload returns actionable validation errors.  
**Priority:** High

**Preconditions:**
- Valid credentials available
- Self-intersecting polygon provided

**Steps:**
1. Send authenticated `POST /estimate` with invalid polygon payload:
```json
{
  "geoShape": {
    "type": "Polygon",
    "coordinates": [[
      [-113.490, 53.540],
      [-113.485, 53.540],
      [-113.485, 53.545],
      [-113.495, 53.542],
      [-113.490, 53.540]
    ]]
  }
}
```

**Expected Results:**
- System returns HTTP 422.
- Response contains:
  - `error`: "validation_failed"
  - `message`: Clear explanation of polygon self-intersection
  - `details.intersection_point`: coordinates of intersection
  - `suggested_fix`: actionable guidance
  - `documentation`: link to geo-shape validation docs
- No estimate is returned.

---

### AT-UC23-006 — Address Not Resolvable
**Objective:** Verify unresolvable addresses return a clear 422-style error.  
**Priority:** High

**Preconditions:**
- Valid credentials available
- ADDR_NONE is not resolvable by geocoder

**Steps:**
1. Send authenticated `POST /estimate` with `ADDR_NONE`.

**Expected Results:**
- System returns HTTP 422 (or domain equivalent).
- Error message indicates address could not be resolved.
- Response suggests providing more detail or using coordinates.
- No estimate is created/cached.

---

### AT-UC23-007 — Ambiguous Address Handling
**Objective:** Verify ambiguous addresses are handled with actionable guidance.  
**Priority:** Medium

**Preconditions:**
- Valid credentials available
- ADDR_AMBIG resolves to multiple candidates

**Steps:**
1. Send authenticated `POST /estimate` with `ADDR_AMBIG`.

**Expected Results:**
- System returns HTTP 422 (or 300/409 per design) indicating ambiguity.
- Response includes candidate suggestions or a disambiguation token (per contract).
- No estimate is returned until disambiguated.

---

### AT-UC23-008 — Partial Results When Optional Data Missing
**Objective:** Verify estimate is returned when optional open data (e.g., crime) is temporarily unavailable.  
**Priority:** High

**Preconditions:**
- Valid credentials available
- Crime statistics dataset simulated as unavailable
- Address "10234 98 Street NW, Edmonton, AB" is resolvable

**Steps:**
1. Simulate crime dataset unavailability
2. Send authenticated `POST /estimate` with address payload

**Expected Results:**
- System returns HTTP 200 (not an error)
- Response contains:
  - `baselineValue`: 425000
  - `estimatedValue`: computed without crime factor
  - `confidence`: reduced (e.g., 78% vs normal 85%)
  - `completeness`: 85% (indicating 1 factor missing)
  - `missingFactors`: ["crime_statistics"]
  - `warnings`: [{"code": "partial_data", "message": "Crime statistics temporarily unavailable..."}]
- Estimate is still usable but flagged as partial
- Response includes `fallback_used`: true metadata  
**Priority:** High

**Preconditions:**
- Valid credentials available
- Property location is in partial-coverage region
- Baseline assessment exists

**Steps:**
1. Simulate crime dataset unavailable (or choose region with no crime data).
2. Send authenticated `POST /estimate` request for that region.

**Expected Results:**
- HTTP 200 returned (not a hard failure).
- Response includes missing-factor list mentioning the unavailable dataset.
- Confidence/completeness score is reduced relative to full-coverage region.
- Factor breakdown excludes missing factor contributions.

---

### AT-UC23-009 — Routing Fallback to Straight-Line Distance
**Objective:** Verify when routing fails, straight-line distance is used and flagged.  
**Priority:** High

**Preconditions:**
- Valid credentials available
- Routing provider can be forced to timeout/fail
- Property requires distance computations

**Steps:**
1. Force routing provider failure/timeout.
2. Send authenticated `POST /estimate` request requiring road distances.

**Expected Results:**
- HTTP 200 returned.
- Response includes a warning/fallback flag indicating straight-line distance was used.
- Confidence/completeness reflects approximation (reduced or annotated).
- Logs/metrics show routing failure and fallback usage incremented.

---

### AT-UC23-010 — Baseline Missing Causes Failure
**Objective:** Verify estimate fails when baseline tax assessment value is unavailable.  
**Priority:** High

**Preconditions:**
- Valid credentials available
- Property located in region with no baseline assessment coverage

**Steps:**
1. Send authenticated `POST /estimate` for a property in baseline-missing region.

**Expected Results:**
- System returns HTTP 422/424 (per design) indicating baseline is required and missing.
- Error identifies missing dataset/region coverage.
- No estimate is produced.

---

### AT-UC23-011 — Caching: Cache Hit Returns Consistent Result
**Objective:** Verify repeated identical requests return cached results and reduce latency.  
**Priority:** High

**Preconditions:**
- Valid credentials available
- Caching enabled
- A successful estimate has been computed for ADDR_FULL with default parameters

**Steps:**
1. Send authenticated `POST /estimate` for ADDR_FULL and record response time.
2. Repeat the exact same request and record response time and any cache indicators.

**Expected Results:**
- Second response is faster (or includes cache-hit indicator).
- Returned estimate payload is consistent with first response (within any allowed rounding).
- Logs/metrics show cache hit on second request.

---

### AT-UC23-012 — Caching: Stale Cache Entry Triggers Recompute
**Objective:** Verify stale cached results are not returned when TTL/version invalidates them.  
**Priority:** Medium

**Preconditions:**
- Valid credentials available
- Caching enabled
- Ability to expire TTL or bump dataset version

**Steps:**
1. Compute an estimate for ADDR_FULL (to populate cache).
2. Expire the cache entry (wait TTL or force invalidation) or simulate dataset version change.
3. Send the same request again.

**Expected Results:**
- System recomputes the estimate (cache miss) rather than returning stale data.
- Response indicates refreshed timestamps (if provided).
- Cache is updated with new entry.

---

### AT-UC23-013 — Correlation ID Present on Success and Failure
**Objective:** Verify correlation IDs are included for traceability.  
**Priority:** Medium

**Preconditions:**
- Valid credentials available

**Steps:**
1. Send a successful estimate request (ADDR_FULL).
2. Send a failing request (POLY_INVALID).

**Expected Results:**
- Both responses include a correlation/trace ID in headers or body.
- Correlation ID can be found in logs for each request.

---

### AT-UC23-014 — Time Budget Exceeded Returns 503
**Objective:** Verify timeouts return controlled errors and do not hang clients.  
**Priority:** Medium

**Preconditions:**
- Valid credentials available
- Ability to force valuation engine slowdown/time budget exceedance

**Steps:**
1. Simulate valuation engine delay beyond configured timeout.
2. Send authenticated estimate request.

**Expected Results:**
- System returns HTTP 503/504 with structured error.
- Response includes correlation ID.
- No partial internal stack trace is exposed.
- Timeout is recorded in metrics/logs.

---

## 7. Traceability to UC-23 Scenario Narratives
- Main success scenario: AT-UC23-002, AT-UC23-003, AT-UC23-004
- Invalid/malformed input: AT-UC23-005, AT-UC23-006, AT-UC23-007
- Missing data / partial results: AT-UC23-008, AT-UC23-010
- Routing fallback: AT-UC23-009
- Caching: AT-UC23-011, AT-UC23-012
- Timeouts/operational traceability: AT-UC23-013, AT-UC23-014
