# Acceptance Test Suite — UC-30: Precompute Grid-Level Features

## 1. Purpose
This suite verifies offline precomputation jobs generate aggregated grid features with correctness checks and robust failure handling.

## 2. Scope
In scope:
- Triggering and completion
- Aggregation and validation
- Persistence with freshness metadata
- Resilience to missing sources and write failures

## 3. Assumptions and Test Data
- Scheduler/runner exists.
- Feature store schema supports grid aggregates.
- Source datasets available with controlled failure simulation.

## 4. Entry and Exit Criteria

### Entry Criteria
- Pipeline deployed and configured.
- Feature store writable.

### Exit Criteria
- All High priority tests pass.

## 5. Test Environment
- Pipeline runner
- Database access for verification

---
## 6. Test Cases

### AT-UC30-001 — Job Runs On Demand
**Objective:** Verify job trigger and success completion.  
**Priority:** High

**Preconditions:**
- Pipeline deployed
- Trigger available

**Steps:**
1. Trigger precompute job.
2. Wait for completion.

**Expected Results:**
- Job success reported.
- Summary metrics produced.

---

### AT-UC30-002 — Freshness Metadata Written
**Objective:** Verify timestamps/versions stored.  
**Priority:** High

**Preconditions:**
- Job completed

**Steps:**
1. Inspect grid tables.
2. Check timestamps/versions.

**Expected Results:**
- Non-null timestamps.
- Version recorded.
- Recent values.

---

### AT-UC30-003 — Mean and Median Aggregates Computed Correctly
**Objective:** Verify mean and median columns are populated with plausible values for each grid cell.  
**Priority:** High

**Preconditions:**
- Precompute job completed successfully
- Schema supports mean/median columns
- Example grid cell C-247 contains 52 properties

**Steps:**
1. Inspect grid_features_v2 table for cell C-247
2. Verify aggregate statistics

**Expected Results:**
- Grid cell C-247 record contains:
  - grid_id: "C-247"
  - bounds: {north: 53.5468, south: 53.5423, east: -113.4912, west: -113.4987}
  - property_stats.count: 52
  - property_stats.mean_baseline_value: 412000 (±87000)
  - property_stats.median_baseline_value: 395000
  - amenity_density.parks_count: 3
  - amenity_density.schools_count: 7
  - walkability_proxy: 72
  - crime_stats.incident_count_12mo: 8
  - crime_stats.crime_rate_per_1000: 2.4
- Mean and median are positive and in reasonable range ($300K-$600K)
- No NaN or null values where data exists
- Standard deviation present and makes sense relative to mean

---

### AT-UC30-004 — Outlier Sanity Checks
**Objective:** Verify outliers flagged or handled robustly.  
**Priority:** Medium

**Preconditions:**
- Outlier condition available

**Steps:**
1. Run job with outlier input.

**Expected Results:**
- Warnings include affected cells.
- Robust handling applied per design.

---

### AT-UC30-005 — Source Unavailable Uses Snapshot/Skips
**Objective:** Verify job handles missing source data.  
**Priority:** Medium

**Preconditions:**
- Snapshot available or skip logic present
- Disable one source dataset

**Steps:**
1. Disable crime dataset.
2. Run job.

**Expected Results:**
- Job completes with warning.
- Snapshot used or feature skipped for that dataset.

---

### AT-UC30-006 — DB Write Failure Retry/Rollback
**Objective:** Verify transactional safety on write failure.  
**Priority:** High

**Preconditions:**
- Can simulate DB write failure

**Steps:**
1. Induce DB write failure.
2. Run job.

**Expected Results:**
- Retries occur.
- On persistent failure, rollback/consistent state ensured.
- Job reports failure.

---

## 7. Traceability
- Job success and persistence: AT-UC30-001 to AT-UC30-003
- Resilience: AT-UC30-005, AT-UC30-006
