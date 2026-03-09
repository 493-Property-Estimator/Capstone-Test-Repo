# Scenario — UC-21: Deduplicate open-data entities

## Scenario Name
Deduplicate POIs across sources into canonical entities (with confidence thresholds, QA, and traceable publication)

## Narrative
Devin is the PVE maintainer responsible for preventing double-counting in downstream “nearby amenities” computations. The system ingests POIs from multiple sources (UC-17) and standardizes their categories (UC-20), but overlapping coverage means the same real-world place can appear multiple times (e.g., a park from a municipal dataset and the same park from OSM).

After adding a new POI source, Devin runs entity deduplication. Devin expects the system to:
* generate candidate duplicates using spatial proximity, name similarity, and category compatibility
* assign confidence scores and merge only high-confidence matches automatically
* preserve provenance and keep links to the original source records for auditability
* avoid over-merging adjacent but distinct entities (e.g., two businesses in the same plaza)
* publish a canonical entity view that downstream feature computation can use without double-counting
* produce a report that highlights low-confidence candidates and merge decisions for review

## Scope
Property Value Estimator (PVE) — Data Governance & Entity Resolution subsystem (Entity Resolution Module + Spatial DB/Feature Store + QA + Publication)

## Actors
* **Primary Actor**: Maintainer (Devin — Data Engineer / Data Steward)
* **Supporting Actors**:
  * Ingestion Pipeline / POI Store (raw POIs with provenance)
  * Category Standardization Output (canonical categories from UC-20)
  * Deduplication / Entity Resolution Module (matching + scoring + merge/link)
  * Spatial Database / Feature Store (staging + production canonical entity tables)
  * QA/Validation Module (over-merge detection, count sanity checks)
  * Logging/Monitoring (run IDs, metrics, alerts)
  * Optional Review Workflow (manual override/approval, if implemented)

## Preconditions
* Multiple POI sources have been ingested and stored with provenance (`source`, `source_id`) (UC-17).
* POIs have standardized canonical categories available (UC-20), or category compatibility rules are otherwise configured.
* A deduplication strategy is configured, including:
  * spatial proximity thresholds (possibly per category)
  * name normalization and similarity function
  * category compatibility rules
  * stable identifier matching rules (when available)
  * confidence scoring and merge thresholds (auto-merge vs review vs reject)
* Data model supports:
  * canonical entity table(s)
  * link table mapping canonical entity → source records
  * retention of source attributes for audit
* Publication/promotion mechanism exists (atomic swap/rename or versioned views).

## Trigger
* A new POI dataset ingestion occurs, or a new source is added.
* Devin initiates a deduplication run (manual or scheduled).

## Main Flow (Success Scenario)
1. Devin initiates a deduplication run for entity type **POIs** (and optionally selects a region or category subset).
2. The system creates a deduplication **run ID** and records the configuration snapshot (thresholds, scoring weights, category compatibility matrix, and input dataset versions).
3. The system loads the candidate pool of POIs, including:
   * geometry (point)
   * standardized canonical category (and subcategory if available)
   * normalized name fields (or raw name for normalization)
   * provenance (`source`, `source_id`)
4. The system groups candidates to reduce search space (e.g., by region tiles and canonical category).
5. For each group, the system generates candidate duplicate pairs/clusters using matching rules:
   * distance within threshold (e.g., 25–100m depending on category)
   * normalized name similarity above threshold
   * category agreement/compatibility
   * stable identifiers match (when present)
6. The entity resolution module assigns a confidence score to each candidate match and determines an action:
   * **auto-merge** (high confidence)
   * **review** (medium confidence)
   * **do not merge** (low confidence)
7. The system constructs canonical entities from auto-merge clusters:
   * selects canonical geometry (e.g., centroid or preferred-source coordinate)
   * chooses canonical name/category using precedence rules (preferred source, highest quality, most recent)
   * retains/records conflicting attributes for audit
8. The system writes results to staging tables:
   * canonical entities
   * canonical-to-source link table (all source records in the cluster)
   * unresolved “review” candidate list with evidence (distance, name scores, category match, sources)
9. The QA module runs checks on staging:
   * count reduction summary by category and source
   * sanity checks for over-merging signals (e.g., unusually large clusters, merges across incompatible categories)
   * distance threshold compliance (no merged pairs beyond max distance)
10. The system generates a deduplication report for Devin including:
   * total entities before/after
   * merges performed, review candidates, and rejected candidates counts
   * categories with unusually high merge rates
   * top sources contributing duplicates
11. QA passes configured thresholds (e.g., over-merge signals below threshold; constraints satisfied).
12. The system publishes deduplicated canonical entities atomically (swap/rename or versioned view update).
13. The system records production metadata (run ID, thresholds/scoring version, counts, warnings).
14. Downstream feature computation queries canonical entities (not raw source POIs) so amenities are not double-counted.

## Postconditions (Success)
* A canonical entity representation is available for POIs, with links to all underlying source records.
* Deduplication decisions are traceable (run ID + evidence + thresholds).
* Downstream computations can rely on canonical entities to avoid double counting while preserving source provenance.

## Variations / Extensions
* **5a — Two entities are close but distinct (avoid over-merge)**
  * 5a1: The system assigns low confidence due to name mismatch/category mismatch and does not auto-merge.
  * 5a2: The pair is added to the review list only if medium confidence; otherwise it is rejected.
* **5b — Category compatibility needed (nearby but different types)**
  * 5b1: The system blocks merges across incompatible categories (e.g., `school` vs `restaurant`) even if distance is small.
  * 5b2: Compatible-category merges (e.g., `park` and `playground` subcategory) follow configured rules.
* **7a — Conflicting attributes across sources**
  * 7a1: The system applies precedence rules to choose canonical name/category/coordinate.
  * 7a2: The system retains the alternate values for audit and exposes them via the link table or an attributes history table.
* **6a — Too many low-confidence candidates produced**
  * 6a1: The system summarizes top reasons (distance threshold too large, name normalization too permissive).
  * 6a2: Devin tightens thresholds or adjusts scoring weights and reruns.
* **8a — Manual review/override workflow (if implemented)**
  * 8a1: Devin reviews medium-confidence candidates and marks them as “merge” or “do not merge”.
  * 8a2: The system applies approved overrides, updates staging, reruns QA, and then publishes.
* **12a — Publication blocked by QA**
  * 12a1: The system blocks publication and retains staging for inspection.
  * 12a2: The report highlights the QA failures (e.g., suspect cluster sizes) and examples.
* **12b — Promotion fails (DB lock/permissions)**
  * 12b1: The system rolls back promotion and leaves prior production canonical entities intact.
  * 12b2: The system reports an actionable DB error and keeps staging for inspection (if configured).

## Data Examples (Illustrative)
Example duplicate cluster evidence (illustrative only):
* Candidate A:
  * Source: `municipal_poi_feed`, Source ID: `M-1001`
  * Name: `Ritchie Park`
  * Canonical category: `park`
  * Coordinate: `(x1, y1)`
* Candidate B:
  * Source: `osm_extract`, Source ID: `O-88210`
  * Name: `Ritchie Park`
  * Canonical category: `park`
  * Coordinate: `(x2, y2)`
* Evidence:
  * Distance: `18m`
  * Name similarity: `0.97`
  * Category compatible: `true`
  * Confidence: `0.93` → `auto-merge`

Example run summary (illustrative only):
* Run ID: `poi_dedupe_2026-02-12_001`
* Input POIs: `48,210`
* Canonical entities: `43,980`
* Auto-merges: `3,950`
* Review candidates: `1,120`
* Promotion: `SUCCESS (atomic)`
* Warnings: `["High merge rate for category=grocery; review thresholds"]`

## Business Rules / Guardrails (Product Requirements)
* Deduplication must preserve provenance: canonical entities must link back to all source records.
* Auto-merge occurs only for high-confidence matches; medium/low confidence must not be merged silently.
* Category compatibility rules must prevent merges that would distort semantics (avoid merging across incompatible categories).
* Publication must be atomic; production canonical entities remain unchanged on failure.
* The system must produce a run report with merge counts, QA outcomes, and review candidates for transparency.

## Acceptance Criteria (Checklist)
* A run ID and configuration snapshot is recorded for every deduplication run.
* Candidate generation uses distance + name + category/stable-ID rules as configured and is deterministic for fixed inputs.
* High-confidence candidates are merged into canonical entities; medium confidence are flagged for review; low confidence are rejected.
* Canonical entities and canonical→source link tables are produced and stored in staging before publication.
* QA checks validate count reduction, cluster sanity, and distance/category constraints before publication.
* Publication is atomic; prior production canonical entities remain unchanged if QA fails or promotion fails.
* The run report includes merges performed, review candidates, rejected counts, and category/source summaries.

## Notes / Assumptions
* Category standardization (UC-20) should be run before deduplication so category compatibility is meaningful.
* Thresholds may need to differ by category (parks vs stores) to avoid over-merging; configuration should allow per-category settings.
