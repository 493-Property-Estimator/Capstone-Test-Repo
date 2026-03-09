# Acceptance Test Suite — UC-29: Cache Frequently Requested Computations

## 1. Purpose
This suite verifies caching provides correct, fresh responses and fails safely.

## 2. Scope
In scope:
- Cache hit/miss
- TTL and version invalidation
- Outage and corruption handling

Out of scope:
- Full perf benchmarking

## 3. Assumptions and Test Data
- Cache service deployed and observable.
- Ability to simulate cache outage and corrupted entries.

## 4. Entry and Exit Criteria

### Entry Criteria
- Cache enabled.
- Estimate API reachable.

### Exit Criteria
- All High priority tests pass.

## 5. Test Environment
- API test runner
- Cache inspection/metrics

---
## 6. Test Cases

### AT-UC29-001 — Cache Miss Then Populate
**Objective:** Verify miss computes and stores entry.  
**Priority:** High

**Preconditions:**
- Cache enabled
- Valid credentials

**Steps:**
1. Send estimate request for new key.
2. Inspect cache/metrics.

**Expected Results:**
- Cache miss on first call.
- Estimate returned.
- Cache entry created with TTL.

---

### AT-UC29-002 — Cache Hit Returns Same Result
**Objective:** Verify hit returns consistent response and lower latency.  
**Priority:** High

**Preconditions:**
- Cache entry exists for "10234 98 Street NW, Edmonton"
- Entry was cached 5 minutes ago (within TTL)

**Steps:**
1. Send identical estimate request again.
2. Measure response time.
3. Check cache headers.

**Expected Results:**
- Cache hit occurs (X-Cache-Status: HIT header).
- Response exactly matches cached result:
  - baselineValue: 425000
  - estimatedValue: 455000
  - confidence: 85
- Response time ~45ms (vs ~180ms uncached).
- Logs show: cache_hit=true

---

### AT-UC29-003 — Normalization Prevents Duplicate Keys
**Objective:** Verify semantically identical requests reuse cache key.  
**Priority:** Medium

**Preconditions:**
- Cache enabled

**Steps:**
1. Send request with different formatting for same address.
2. Repeat with normalized formatting.

**Expected Results:**
- Second call hits cache.
- Results consistent.

---

### AT-UC29-004 — TTL Expiration Causes Recompute
**Objective:** Verify expired entries are recomputed.  
**Priority:** High

**Preconditions:**
- TTL can be expired

**Steps:**
1. Compute and cache estimate.
2. Expire TTL.
3. Send again.

**Expected Results:**
- Cache miss occurs.
- Estimate recomputed.
- Cache refreshed.

---

### AT-UC29-005 — Dataset Version Invalidation
**Objective:** Verify version bump invalidates cached entries.  
**Priority:** Medium

**Preconditions:**
- Dataset version bump possible

**Steps:**
1. Cache an estimate.
2. Bump dataset version.
3. Send again.

**Expected Results:**
- Cached entry treated stale.
- Recompute occurs.
- Cache updated.

---

### AT-UC29-006 — Cache Unavailable Does Not Break Estimate
**Objective:** Verify estimate works when cache is down.  
**Priority:** High

**Preconditions:**
- Can stop cache service

**Steps:**
1. Stop cache service.
2. Request estimate.

**Expected Results:**
- Estimate returned successfully.
- Cache warning logged.
- No hard failure.

---

### AT-UC29-007 — Corrupted Cache Entry Discarded
**Objective:** Verify corrupted entry triggers recompute.  
**Priority:** Medium

**Preconditions:**
- Can inject corrupted entry

**Steps:**
1. Inject corrupted cache value.
2. Send request.

**Expected Results:**
- System discards corrupted value.
- Recomputes and overwrites cache.
- No crash.

---

## 7. Traceability
- Cache behavior: AT-UC29-001 to AT-UC29-004
- Resilience: AT-UC29-006, AT-UC29-007
