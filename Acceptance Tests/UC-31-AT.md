# Acceptance Test Suite — UC-31: Provide Health Checks and Service Metrics

## 1. Purpose
This suite verifies health and metrics endpoints support monitoring and alerting with accurate dependency reporting and safe exposure.

## 2. Scope
In scope:
- Health status levels
- Dependency checks
- Metrics content
- Protection and redaction

## 3. Assumptions and Test Data
- Endpoints deployed.
- Ability to simulate dependency failures.

## 4. Entry and Exit Criteria

### Entry Criteria
- Services reachable.
- Permission to access endpoints.

### Exit Criteria
- All High priority tests pass.

## 5. Test Environment
- API client
- Dependency toggling capability

---
## 6. Test Cases

### AT-UC31-001 — Health Healthy
**Objective:** Verify healthy status when all deps up.  
**Priority:** High

**Preconditions:**
- All deps operational

**Steps:**
1. Call `GET /health`.

**Expected Results:**
- HTTP 200.
- Status Healthy.
- Deps OK.

---

### AT-UC31-002 — Health Degraded on Routing Down
**Objective:** Verify degraded status returned when routing provider down but fallback exists.  
**Priority:** High

**Preconditions:**
- Routing provider (GraphHopper) simulated as down
- Straight-line fallback enabled
- All other dependencies healthy

**Steps:**
1. Call `GET /health`
2. Parse response JSON

**Expected Results:**
- HTTP 200 returned (service operational)
- Response status: "degraded"
- Response message: "Non-critical dependency unavailable: Routing Provider. Service operating with reduced functionality."
- Dependencies breakdown shows:
  - routing_provider.status: "down"
  - routing_provider.error: "Connection refused"
  - routing_provider.impact: "Falling back to straight-line distance calculations"
  - feature_store.status: "up"
  - cache_service.status: "up"
  - valuation_engine.status: "up"
- Monitoring system logs WARNING alert
- Estimate requests continue to succeed using fallback

---

### AT-UC31-003 — Health Unhealthy on Feature Store Down
**Objective:** Verify unhealthy when feature store down.  
**Priority:** High

**Preconditions:**
- Feature store down

**Steps:**
1. Call `GET /health`.

**Expected Results:**
- Status Unhealthy.
- Feature store failure indicated.

---

### AT-UC31-004 — Metrics Expose Core Counters
**Objective:** Verify /metrics includes counts/latency/domain metrics.  
**Priority:** High

**Preconditions:**
- Metrics enabled

**Steps:**
1. Generate traffic (success + failure).
2. Call `GET /metrics`.

**Expected Results:**
- Request count and error count present.
- Latency metric present.
- Cache hit and fallback usage present if implemented.

---

### AT-UC31-005 — Metrics Redaction
**Objective:** Verify no raw addresses/PII in metrics.  
**Priority:** Medium

**Preconditions:**
- Metrics enabled

**Steps:**
1. Scan metrics output for test addresses/IDs.

**Expected Results:**
- No raw PII present.
- Only aggregated labels.

---

### AT-UC31-006 — Health Rate Limited
**Objective:** Verify protection against excessive polling.  
**Priority:** Low

**Preconditions:**
- Rate limiting configured

**Steps:**
1. Burst health requests beyond limit.

**Expected Results:**
- 429 (or similar) for excess.
- Service stable.

---

## 7. Traceability
- Health: AT-UC31-001 to AT-UC31-003
- Metrics: AT-UC31-004, AT-UC31-005
