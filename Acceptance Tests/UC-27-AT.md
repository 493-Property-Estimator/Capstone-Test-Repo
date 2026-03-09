# Acceptance Test Suite — UC-27: Fall Back to Straight-Line Distance When Routing Fails

## 1. Purpose
This suite verifies routing failures trigger straight-line fallback, allow estimates to proceed, and are clearly flagged and observable.

## 2. Scope
In scope:
- Failure detection
- Straight-line fallback computation
- Mixed-mode handling
- Observability

Out of scope:
- Routing provider correctness

## 3. Assumptions and Test Data
- Routing provider can be forced to succeed/fail/partially fail.
- Property and amenity coordinates available.

## 4. Entry and Exit Criteria

### Entry Criteria
- Distance service deployed.
- Ability to simulate routing failure.
- Estimate API accessible for observation.

### Exit Criteria
- All High priority tests pass.

## 5. Test Environment
- API test runner
- Logs/metrics access

---
## 6. Test Cases

### AT-UC27-001 — Road Distance Preferred When Available
**Objective:** Verify road distance used when routing healthy.  
**Priority:** High

**Preconditions:**
- Routing provider healthy

**Steps:**
1. Request estimate with distance outputs.

**Expected Results:**
- Road distances used.
- No fallback flag.

---

### AT-UC27-002 — Fallback Activated on Timeout
**Objective:** Verify routing timeout triggers straight-line fallback and flags it in response.  
**Priority:** High

**Preconditions:**
- Routing provider (GraphHopper) simulated to timeout after 3000ms
- Fallback to straight-line distance enabled
- Property at coordinates (53.5461°N, -113.4938°W)
- Target amenity: nearest school at (53.5445°N, -113.4912°W)

**Steps:**
1. Request estimate for property
2. Routing service times out attempting to compute road distance

**Expected Results:**
- Estimate completes successfully (HTTP 200)
- Response includes:
  - Distance to school: 220m (straight-line via Haversine formula)
  - `fallback_used`: true
  - `fallback_reason`: "routing_timeout"
  - `distance_method`: "straight_line"
- Warning message: "Road routing unavailable. Estimate uses straight-line distances as approximation."
- Confidence reduced slightly (e.g., 83% vs normal 85%)
- Logs show: routing_timeout=true, fallback=straight_line, response_time=3100ms

---

### AT-UC27-003 — Mixed-Mode Distances
**Objective:** Verify partial routing failures produce mixed-mode result.  
**Priority:** Medium

**Preconditions:**
- Partial routing failures possible
- Fallback enabled

**Steps:**
1. Request estimate with multiple targets.
2. Force partial failures.

**Expected Results:**
- Road for some targets, straight-line for others.
- Mixed-mode indicators present.
- Estimate completes.

---

### AT-UC27-004 — Fallback Disabled Causes Error
**Objective:** Verify failure when fallback disabled and routing fails.  
**Priority:** Medium

**Preconditions:**
- Fallback disabled
- Routing fails

**Steps:**
1. Request estimate requiring routing distances.

**Expected Results:**
- Controlled error returned (503/424).
- Correlation ID present.

---

### AT-UC27-005 — Missing Coordinates Prevent Fallback
**Objective:** Verify invalid coords prevent fallback computation.  
**Priority:** High

**Preconditions:**
- Invalid coordinates provided
- Routing fails

**Steps:**
1. Send estimate request with invalid coordinates.

**Expected Results:**
- Validation error 400/422.
- No distances computed.

---

### AT-UC27-006 — Fallback Usage Logged
**Objective:** Verify logs/metrics track fallback usage.  
**Priority:** Medium

**Preconditions:**
- Metrics/log access
- Routing fails

**Steps:**
1. Trigger routing failure request.
2. Inspect metrics/logs.

**Expected Results:**
- Fallback counter incremented.
- Logs include correlation ID and failure cause.

---

## 7. Traceability
- Fallback activation: AT-UC27-002
- Mixed mode: AT-UC27-003
- Failure when disabled: AT-UC27-004
