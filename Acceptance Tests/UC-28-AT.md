# Acceptance Test Suite — UC-28: Provide Partial Results When Some Open Data is Unavailable

## 1. Purpose
This suite verifies estimates remain usable under missing open-data, with transparent reporting and confidence degradation.

## 2. Scope
In scope:
- Partial estimates
- Missing factor reporting
- Reliability threshold handling
- Timeout strategies

Out of scope:
- UI warning rendering

## 3. Assumptions and Test Data
- Regions with full/partial/sparse coverage exist.
- Ability to simulate dataset outages and timeouts.

## 4. Entry and Exit Criteria

### Entry Criteria
- Estimate API deployed.
- Feature store seeded.
- Ability to disable datasets.

### Exit Criteria
- All High priority tests pass.

## 5. Test Environment
- API test runner
- Dataset toggling/mocking

---
## 6. Test Cases

### AT-UC28-001 — Partial Result When One Dataset Missing
**Objective:** Verify estimate returns with missing factor list and reduced confidence when one optional dataset unavailable.  
**Priority:** High

**Preconditions:**
- Baseline assessment present for property "10234 98 Street NW, Edmonton"
- Crime statistics dataset simulated as unavailable (HTTP 503)
- All other datasets available (schools, parks, stores, comparables)

**Steps:**
1. Request estimate via API or UI
2. Observe response warnings and confidence

**Expected Results:**
- HTTP 200 returned (successful partial result)
- Response contains:
  - baselineValue: 425000
  - estimatedValue: 448000 (computed without crime factor)
  - confidence: 78 (reduced from normal ~85)
  - completeness: 85 (5 of 6 factors)
  - missingFactors: ["crime_statistics"]
  - warnings: [{"code": "partial_data", "message": "Crime statistics temporarily unavailable. Estimate computed with available data."}]
- Factor breakdown shows 5 factors computed, 1 missing
- UI displays yellow warning banner about partial data

---

### AT-UC28-002 — Comparables Missing => Low Confidence
**Objective:** Verify baseline-based estimate still returns with low confidence when comparables missing.  
**Priority:** High

**Preconditions:**
- Baseline present
- Comparables unavailable

**Steps:**
1. Request estimate.

**Expected Results:**
- Estimate returned (unless comparables critical).
- Very low confidence.
- Missing factor includes comparables.

---

### AT-UC28-003 — Too Many Missing Factors Handling
**Objective:** Verify reliability handling when missing factors exceed threshold.  
**Priority:** High

**Preconditions:**
- Baseline present
- Multiple datasets missing

**Steps:**
1. Request estimate.

**Expected Results:**
- Response indicates low reliability (200+warning or 206).
- Missing factors listed.
- No silent success.

---

### AT-UC28-004 — Baseline Missing Fails
**Objective:** Verify baseline missing returns controlled failure.  
**Priority:** High

**Preconditions:**
- Baseline absent

**Steps:**
1. Request estimate.

**Expected Results:**
- HTTP 422/424 returned.
- Error indicates baseline required.

---

### AT-UC28-005 — Dataset Timeout Uses Cache/Skip
**Objective:** Verify timeouts do not hang; system retries/uses cache/omits factor.  
**Priority:** Medium

**Preconditions:**
- Baseline present
- Can simulate dataset timeout

**Steps:**
1. Simulate timeout.
2. Request estimate.

**Expected Results:**
- Bounded retry or cached snapshot used.
- If still unavailable, factor omitted and flagged.
- Request completes.

---

### AT-UC28-006 — Strict Mode Requires Factors (If Supported)
**Objective:** Verify strict mode rejects missing required factor.  
**Priority:** Medium

**Preconditions:**
- Strict mode supported
- Required factor unavailable

**Steps:**
1. Request estimate with strict requirement for missing factor.

**Expected Results:**
- Error returned indicating required factor unavailable.
- Missing required datasets listed.

---

## 7. Traceability
- Partial estimates: AT-UC28-001, AT-UC28-002
- Reliability threshold: AT-UC28-003
- Critical baseline: AT-UC28-004
