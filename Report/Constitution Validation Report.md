# Constitution Validation Report

**Project:** Property Value Estimator  
**Date:** 2026-03-13  
**Reviewer:** Codex

## Scope

This report validates `.specify/memory/constitution.md` against:
- `overview_updated.md`
- `Property_Value_Estimator_User_Stories_Updated.md`

## Validation Outcome

The constitution is directionally strong on engineering quality, testing, UX consistency, and performance governance.  
However, it does not fully encode several domain-critical requirements from the source documents and includes one potentially over-restrictive constraint.

## Findings (Prioritized)

### 1) High: Stack constraint is over-restrictive and not source-traceable
- **Constitution reference:** `.specify/memory/constitution.md` line 47
- **Issue:** The constitution mandates only vanilla HTML/CSS/JS + Python.
- **Source comparison:** `overview_updated.md` and user stories do not require this strict stack limitation.
- **Risk:** Limits practical implementation options for mapping/routing/data ingestion components needed by the product scope.

### 2) High: Open-data-only governance is missing as a constitutional rule
- **Source reference:** `Property_Value_Estimator_User_Stories_Updated.md` line 79 (Epic 4: Open Data Only)
- **Issue:** Constitution does not explicitly enforce open-data-only data policy.
- **Risk:** Future specs may drift toward non-open/proprietary data sources, violating core project intent.

### 3) Medium: Resilience and fallback behavior is not codified
- **Source references:** `overview_updated.md` line 16; user stories lines 127 and 131
- **Issue:** Missing constitutional requirement for:
  - fallback to straight-line distance when routing fails
  - partial results when some data is unavailable
- **Risk:** Functional resilience may be treated as optional rather than mandatory.

### 4) Medium: Explainability output contract is not explicitly governed
- **Source references:** user stories lines 61, 65, 69, 73; `overview_updated.md` line 33
- **Issue:** Constitution does not require the valuation output to include:
  - single estimate
  - low/high range
  - top contributing factors
  - baseline anchoring to assessment value
- **Risk:** Output quality may vary across implementations and lose transparency.

### 5) Medium: Data freshness and normalization quality gates are missing
- **Source references:** `overview_updated.md` lines 20-22; user stories lines 93, 97, 101
- **Issue:** No constitutional obligations for:
  - scheduled data refresh
  - POI category standardization
  - deduplication
- **Risk:** Model quality and consistency can degrade over time.

### 6) Low: Performance thresholds are specific but lack traceable basis
- **Constitution reference:** lines 40-43
- **Issue:** p95 latency targets are present, but source docs specify only “fast and responsive.”
- **Risk:** Teams may fail strict gates that were never explicitly ratified from source requirements.

### 7) Low: Governance metadata incomplete
- **Constitution reference:** line 74
- **Issue:** Ratification date is unresolved (`TODO`).
- **Risk:** Formal governance history is incomplete.

## Alignment Snapshot

### Strongly aligned
- Engineering quality expectations
- Testing as release gate
- UX consistency expectations
- Performance considered as a mandatory review area

### Partially or not aligned
- Open-data-only policy
- Resilience fallback requirements
- Explainability output contract
- Data refresh/standardization/dedup governance
- Traceability of hard numerical SLOs

## Recommended Constitution Updates

1. Add an explicit **Data Policy Principle**: only open data sources unless constitution amendment is approved.
2. Add a **Resilience Principle** requiring graceful degradation and partial-result behavior.
3. Add an **Explainability Principle** requiring estimate + range + top factors + baseline attribution.
4. Add **Data Quality/Freshness gates** for refresh cadence, standardization, and deduplication.
5. Reframe stack rule from hard restriction to preferred baseline unless justified.
6. Add rationale source for current p95 targets, or soften to measurable SLOs to be set per release.
7. Resolve ratification metadata.

## Assumptions

1. The two provided basis documents are authoritative for constitutional intent.
2. Validation scope is governance-document alignment, not runtime code behavior.
