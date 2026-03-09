# Scenario — UC-20: Standardize POI categories across sources

## Scenario Name
Standardize POI categories using a canonical taxonomy (with mapping QA and traceable promotion)

## Narrative
Casey is the PVE data steward responsible for making sure that “nearby amenities” features mean the same thing across all data sources. The system ingests POIs from multiple open-data feeds (UC-17), but each feed uses its own categories (e.g., “Playground”, “Parks & Rec”, “Green Space”, “School - Public”, “Primary School”).

Casey needs a single canonical taxonomy (e.g., School, Park, Hospital, Grocery, Transit) so feature computation can compare locations consistently. Casey updates the taxonomy/mapping rules and triggers a standardization run. Casey expects that:
* raw source categories are preserved for traceability
* canonical categories/subcategories are assigned deterministically by rules
* mapping quality is measurable (mapped %, unmapped %, conflicts) and thresholded
* unmapped labels are reported so the taxonomy can be improved
* promotion is safe and atomic so downstream feature computation always uses a coherent classification

## Scope
Property Value Estimator (PVE) — Data Governance & Feature Semantics subsystem (Taxonomy + Category Mapping + POI Store + QA + Promotion)

## Actors
* **Primary Actor**: Maintainer (Casey — Data Steward / Data Engineer)
* **Supporting Actors**:
  * Canonical Category Taxonomy (definitions, allowed labels, hierarchy)
  * Mapping Rules / Rules Engine (lookup tables, regex rules, precedence)
  * Ingestion Pipeline / POI Store (raw POIs + standardized POIs, staging + production)
  * Upstream POI Sources (municipal portal, OSM-derived feeds, etc.)
  * Validation/QA Module (mapping quality metrics, conflict detection)
  * Logging/Monitoring (run IDs, mapping coverage trends)

## Preconditions
* POIs have already been ingested and stored with provenance (source name + source ID) and raw category fields (UC-17).
* A canonical taxonomy exists (categories and optional subcategories) with stable identifiers (e.g., `park`, `school`, `hospital`).
* Mapping mechanism exists to translate source-specific category fields into canonical categories.
* Governance policy is defined for unmapped labels (block promotion vs allow “Unmapped/Other” with warnings).
* Production consumers (feature computation) can read standardized categories (and optionally fall back to raw categories when explicitly requested).

## Trigger
* A new POI dataset is ingested.
* A new POI source is added.
* Casey updates the taxonomy/mapping rules and initiates a reclassification run.

## Main Flow (Success Scenario)
1. Casey opens the taxonomy configuration and reviews the canonical categories used by the valuation system (e.g., School, Park, Grocery, Hospital, Transit).
2. Casey confirms that raw POIs from one or more sources are present in the database with raw category fields recorded (UC-17).
3. Casey initiates a “POI category standardization” run and selects the target sources (or “all sources”).
4. The system creates a **run ID** and records a snapshot of:
   * taxonomy version (or commit hash)
   * mapping rules version
   * targeted sources and processing mode (full reprocess vs incremental)
5. The system reads raw POIs and applies mapping rules to assign:
   * canonical category (required)
   * optional canonical subcategory (if enabled)
   * mapping rationale (e.g., rule ID / matched pattern / lookup key) for audit
6. The system writes standardized results to staging tables, storing alongside each POI:
   * source + source ID (provenance)
   * raw category fields (as-ingested)
   * canonical category/subcategory
   * mapping metadata (rule ID/version, timestamp)
7. The QA module computes mapping quality metrics on staging:
   * mapped vs unmapped percentage
   * top unmapped raw labels (counts by source)
   * conflict detection (same raw label mapped to multiple canonical categories)
   * category distribution sanity checks (unexpected spikes/drops vs previous run)
8. The system generates a run report for Casey with the quality metrics and a prioritized list of unmapped labels to classify.
9. QA passes the configured thresholds (e.g., unmapped rate below threshold; conflicts resolved or below threshold).
10. The system promotes standardized POI categories from staging → production atomically (swap/rename or versioned view update).
11. The system records production version metadata (run ID, taxonomy/mapping versions, coverage metrics, warnings).
12. Downstream feature computation now uses the standardized categories to compute amenity proximity and desirability features consistently.

## Postconditions (Success)
* Production POI tables include both raw source categories and standardized canonical categories.
* Mapping coverage metrics and taxonomy/mapping versions are recorded and traceable by run ID.
* Feature computation can rely on consistent POI category semantics across sources.

## Variations / Extensions
* **5a — New/unrecognized source categories appear**
  * 5a1: The system assigns `Unmapped/Other` (or equivalent) and records the raw label and source.
  * 5a2: The run report lists new unmapped labels with counts by source for Casey to classify.
* **5b — A source provides multiple category fields (type + subtype)**
  * 5b1: The system applies precedence rules (prefer subtype when present) and records the rationale.
  * 5b2: The system stores both raw fields to allow later reprocessing as taxonomy evolves.
* **7a — Conflict detected for the same raw label**
  * 7a1: QA flags conflicts (e.g., “Community Centre” mapped to both `recreation` and `school`).
  * 7a2: Casey reviews conflicts and updates mapping rules (disambiguation by additional fields, source, or keyword patterns).
  * 7a3: Casey reruns standardization; promotion is blocked until conflicts meet the governance threshold.
* **7b — Mapping quality below threshold**
  * 7b1: If governance policy is “block”, the system blocks promotion and keeps existing production categories.
  * 7b2: If governance policy is “allow”, the system promotes with explicit warnings and an `unmapped` flag per POI (for downstream filtering).
* **10a — Reclassification after taxonomy change**
  * 10a1: Casey updates the canonical taxonomy (rename/split/merge categories).
  * 10a2: The system reruns classification from stored raw categories (no re-download needed) and produces a new production version.
* **12a — Downstream wants both canonical and raw categories**
  * 12a1: The system exposes both fields to feature computation and analytics.
  * 12a2: Reports and debugging tools can show “raw → canonical” mappings for a POI.

## Data Examples (Illustrative)
Example mapping outcomes (illustrative only):
* Source: `municipal_poi_feed`
  * Raw category: `Playground`
  * Canonical category: `park`
  * Canonical subcategory: `playground`
  * Rule: `regex: playground|play area`
* Source: `school_registry`
  * Raw category: `School - Public`
  * Canonical category: `school`
  * Canonical subcategory: `public`
  * Rule: `lookup: school_type=public`
* Source: `osm_extract`
  * Raw category: `amenity=clinic`
  * Canonical category: `healthcare`
  * Canonical subcategory: `clinic`
  * Rule: `lookup: osm_amenity`

Example run summary (illustrative only):
* Run ID: `poi_cat_2026-02-12_001`
* Taxonomy version: `v3`
* Mapping rules version: `2026-02-10`
* Mapped: `96.2%`
* Unmapped: `3.8%` (top labels: `["Rec Facility", "Community Hub"]`)
* Conflicts: `0` (or list of flagged labels)
* Promotion: `SUCCESS (atomic)`

## Business Rules / Guardrails (Product Requirements)
* Raw source categories must be retained in storage for traceability and future reprocessing.
* Canonical category assignment must be deterministic for the same input under the same taxonomy/mapping versions.
* Mapping quality must be measurable and thresholded; failures block promotion under “strict governance” mode.
* Conflicts (same raw label mapping to multiple canonical categories) must be detected and reported.
* Promotions must be atomic; production consumers must not see a partially standardized state.
* Taxonomy/mapping versions and run IDs must be recorded alongside production data for auditability.

## Acceptance Criteria (Checklist)
* The system records a run ID and taxonomy/mapping version snapshot for every standardization run.
* Standardized POIs store raw categories + canonical categories + mapping rationale.
* QA reports mapped/unmapped rates, top unmapped labels, and conflict detections.
* Governance policy is enforced (block or warn-and-promote) and is visible in the run report.
* Promotion is atomic; production remains unchanged if promotion fails or QA blocks the run (in strict mode).
* Reclassification can be rerun from stored raw categories without re-downloading POIs.

## Notes / Assumptions
* Deduplication/entity resolution is handled separately (UC-21); this scenario focuses on semantic standardization of categories.
* Exact taxonomy depth (category/subcategory) and thresholds are configuration-driven and may evolve.
