# Acceptance Test Suite — UC-26: Show Missing-Data Warnings in UI

## 1. Purpose
This suite verifies the UI accurately communicates missing/approximated data and confidence levels to prevent over-trust of estimates.

## 2. Scope
In scope:
- Parsing missing-factor metadata
- Confidence indicator rendering
- Warning severity handling
- Dismiss/restore behaviors

Out of scope:
- Valuation correctness

## 3. Assumptions and Test Data
- Properties for full/partial/fallback/low-confidence scenarios exist.
- Estimate API returns missing factors + confidence/completeness.

## 4. Entry and Exit Criteria

### Entry Criteria
- UI deployed.
- Estimate API reachable.
- Ability to simulate missing datasets/fallback.

### Exit Criteria
- All High priority tests pass.

## 5. Test Environment
- Browser UI
- Devtools/proxy for observing API responses

---
## 6. Test Cases

### AT-UC26-001 — No Warnings for Full Coverage
**Objective:** Verify full-coverage estimate shows high confidence and no warnings.  
**Priority:** High

**Preconditions:**
- UI loaded
- Full-coverage property available

**Steps:**
1. Select full-coverage property.
2. Request estimate.

**Expected Results:**
- High confidence shown.
- No missing-data warnings.
- Full breakdown present.

---

### AT-UC26-002 — Warning for Missing Optional Dataset
**Objective:** Verify missing optional dataset produces specific warning and reduced confidence.  
**Priority:** High

**Preconditions:**
- UI loaded
- Property at "10234 98 Street NW" selected
- Crime statistics dataset simulated as unavailable

**Steps:**
1. Request estimate for property
2. Observe UI warning indicators

**Expected Results:**
- Yellow warning banner appears with message:
  "Partial Data: Crime statistics temporarily unavailable. Estimate uses incomplete data."
- Confidence indicator shows 78% (reduced from normal 85%)
- Completeness shows "5 of 6 factors" or "85% complete"
- Factor breakdown shows:
  - Schools: +$12,000 ✓
  - Parks: +$8,000 ✓
  - Stores: +$6,000 ✓
  - Comparable properties: +$4,000 ✓
  - Transit: +$3,000 ✓
  - Crime: (unavailable) ⚠
- Help tooltip explains missing dataset impact

---

### AT-UC26-003 — Fallback Messaging for Routing Failure
**Objective:** Verify routing fallback shows specific approximation message.  
**Priority:** High

**Preconditions:**
- UI loaded
- Routing failure simulated

**Steps:**
1. Request estimate while routing is down.

**Expected Results:**
- Message indicates straight-line used.
- Estimate displayed.
- Confidence reflects approximation.

---

### AT-UC26-004 — High Severity Banner for Very Low Confidence
**Objective:** Verify very low confidence triggers prominent banner.  
**Priority:** High

**Preconditions:**
- UI loaded
- Low-confidence property exists

**Steps:**
1. Request estimate for low-confidence property.

**Expected Results:**
- Prominent warning displayed.
- Details expandable.
- User not blocked from viewing estimate.

---

### AT-UC26-005 — Warnings Expand for Details
**Objective:** Verify warning panel is expandable with factor details.  
**Priority:** Medium

**Preconditions:**
- UI loaded
- Estimate returns missing factors list

**Steps:**
1. Expand the warning panel.

**Expected Results:**
- List of missing/approximated factors shown.
- Explanation of impact shown.
- Layout remains usable.

---

### AT-UC26-006 — Dismiss Keeps Indicator
**Objective:** Verify dismiss keeps small persistent indicator.  
**Priority:** Medium

**Preconditions:**
- Warning visible

**Steps:**
1. Dismiss/collapse warning panel.

**Expected Results:**
- Panel collapses.
- Indicator remains.
- Indicator restores panel when clicked.

---

### AT-UC26-007 — Malformed Metadata Graceful Handling
**Objective:** Verify UI handles incomplete metadata without crash.  
**Priority:** Medium

**Preconditions:**
- Ability to simulate response missing completeness field

**Steps:**
1. Request estimate with malformed metadata.

**Expected Results:**
- No crash.
- Generic warning shown.
- Issue logged for debugging.

---

## 7. Traceability
- Full coverage behavior: AT-UC26-001
- Partial/fallback/low-confidence warnings: AT-UC26-002 to AT-UC26-004
- Usability behaviors: AT-UC26-005, AT-UC26-006
