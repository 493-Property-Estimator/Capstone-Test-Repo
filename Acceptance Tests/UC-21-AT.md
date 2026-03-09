# Acceptance Tests — UC-21: Deduplicate open-data entities

## Purpose
Verify that the system deduplicates open-data entities (especially POIs) across sources so downstream computations do not double-count amenities/signals. Verify candidate generation (distance/name/category/stable IDs), confidence scoring thresholds (auto-merge vs review vs reject), provenance-preserving canonical entities with source links, QA checks to prevent over-merging, and atomic publication/rollback.

## References
* User Story: **US-21: Deduplicate open-data entities**
* Use Case: `Use Cases/UC-21.md`
* Scenario: `Scenarios/SC-UC-21.md`
* Related Use Case: `Use Cases/UC-17.md` (POI ingestion with provenance)
* Related Use Case: `Use Cases/UC-20.md` (standardized categories improve matching)

## Assumptions (minimal)
* POIs are stored with provenance (`source`, `source_id`) and coordinates/geometry.
* Canonical categories exist (ideally from UC-20), or category compatibility rules are configured.
* Deduplication produces:
  * canonical entity table(s)
  * canonical→source link table
  * review candidate list for medium-confidence matches
* Publication is atomic (swap/rename or versioned view update).
* A deterministic run configuration exists (thresholds/scoring rules fixed per run).

## Test Data Setup
Prepare controlled POI datasets across multiple sources:
* **D1 (Happy path duplicates)**: Same real-world POIs appear in ≥2 sources with near-identical names/categories and close coordinates.
* **D2 (Close but distinct)**: Two distinct entities within proximity threshold (e.g., adjacent businesses) with different names/categories.
* **D3 (Category mismatch)**: Close coordinates but incompatible categories (should not merge).
* **D4 (Stable ID match)**: Same entity shares a stable identifier across sources (should merge even with minor name differences).
* **D5 (Attribute conflicts)**: Same entity has conflicting names/coordinates/categories across sources (should merge with precedence rules).
* **D6 (Many low-confidence candidates)**: Config/data that produces excessive medium/low confidence matches (threshold tuning scenario).
* **D7 (QA fail / over-merge signal)**: Data that yields unusually large clusters or merge rates beyond thresholds.
* **D8 (Promotion failure)**: Induced DB lock/permission failure during publication.
* Ensure a known last known-good canonical entity production version exists before each negative test.

## Acceptance Test Suite (Gherkin-style)

### AT-21-01 — End-to-end deduplication produces canonical entities and source links (happy path)
**Given** POIs are ingested from multiple sources for **D1** with provenance and geometry  
**When** the maintainer runs deduplication  
**Then** the system produces canonical entities in staging  
**And** produces a canonical→source link table containing all contributing source records  
**And** produces a run report including run ID, thresholds/scoring version, and counts (before/after).

### AT-21-02 — Candidate generation uses distance + name + category/stable-ID rules
**Given** deduplication is run on a dataset containing **D1** and **D4** patterns  
**When** candidate matches are generated  
**Then** candidates are produced when distance is within configured threshold  
**And** name similarity and category compatibility rules are applied  
**And** stable identifier matches (when present) are considered and can raise confidence appropriately  
**And** the run report records the configuration snapshot used for candidate generation.

### AT-21-03 — Confidence thresholds: high confidence auto-merge, medium confidence review, low confidence reject
**Given** the dataset includes high/medium/low confidence examples (**D1**, **D2**, **D3**)  
**When** scoring is performed  
**Then** high-confidence matches are auto-merged into canonical entities  
**And** medium-confidence matches are placed into a review list and are not merged silently  
**And** low-confidence matches are not merged.

### AT-21-04 — Determinism: same inputs + same config yields same merges
**Given** the same input POIs and the same deduplication configuration  
**When** deduplication is run multiple times  
**Then** the canonical entity assignments (which source records map to which canonical entity) are identical  
**And** the system records distinct run IDs/timestamps per run.

### AT-21-05 — Close but distinct entities are not auto-merged (over-merge protection)
**Given** the dataset includes **D2** (adjacent distinct entities)  
**When** deduplication runs  
**Then** those entities are not auto-merged  
**And** they appear as review candidates only if confidence meets the review threshold, otherwise they are rejected  
**And** the run report includes over-merge-related QA checks (cluster size limits or category mismatch constraints).

### AT-21-06 — Incompatible categories do not merge even if spatially close
**Given** the dataset includes **D3** (close but incompatible categories)  
**When** deduplication runs  
**Then** the system does not merge entities across incompatible categories  
**And** the reason for non-merge is consistent with configured category compatibility rules.

### AT-21-07 — Stable ID match can merge despite minor name differences
**Given** the dataset includes **D4** where stable identifiers match across sources  
**When** scoring runs  
**Then** the system merges the records into one canonical entity  
**And** the evidence (stable ID match) is captured in merge rationale or run diagnostics (as supported).

### AT-21-08 — Conflicting attributes are resolved by precedence rules and remain auditable
**Given** the dataset includes **D5** where sources disagree on name/coordinates/category details  
**When** a canonical entity is constructed  
**Then** the system applies precedence rules (preferred source, highest quality, most recent)  
**And** retains links to all source records  
**And** conflicting values are preserved for audit (either in link attributes, history, or run report).

### AT-21-09 — QA checks detect suspicious merges and can block publication
**Given** the dataset includes **D7** designed to trigger over-merge signals (e.g., huge clusters, high merge rate)  
**When** QA runs on staging outputs  
**Then** QA fails with actionable reasons (cluster size, merge rate anomaly, distance violations, incompatible-category merges)  
**And** publication is blocked  
**And** production canonical entities remain unchanged.

### AT-21-10 — Atomic publication: downstream reads a consistent canonical entity version
**Given** a deduplication run passes QA on staging  
**When** publication occurs  
**Then** canonical entities and link tables are updated atomically  
**And** downstream consumers never see a mixture of old and new canonical versions for the same run  
**And** production version metadata references the run ID.

### AT-21-11 — Publication failure rolls back cleanly and preserves last known-good version
**Given** a run passes staging and QA  
**And** publication is forced to fail using **D8**  
**When** the system attempts publication  
**Then** the system reports publication failure with actionable DB error details  
**And** production canonical entities remain on the last known-good version  
**And** the failed run is not recorded as a successful production version.

### AT-21-12 — Downstream feature computation does not double-count using canonical entities
**Given** canonical entities are published successfully for **D1**  
**When** a downstream query counts amenities by canonical category within a radius  
**Then** the count corresponds to canonical entities (not raw records)  
**And** the same real-world place present in multiple sources contributes only once.

## Non-Functional Acceptance Criteria (verifiable)
* **Performance**: Deduplication completes within an agreed window for target POI volumes and configured thresholds.
* **Reliability**: Failures (QA, publication) do not corrupt production; low-confidence matches are not silently merged.
* **Auditability**: Each run is traceable via run ID and records configuration snapshot, merge counts, review candidates, QA outcomes, and publication status.
