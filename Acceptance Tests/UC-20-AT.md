# Acceptance Tests — UC-20: Standardize POI categories across sources

## Purpose
Verify that the system standardizes POI categories across multiple sources using a canonical taxonomy, preserves raw source categories for traceability, measures mapping quality (mapped/unmapped/conflicts), enforces governance thresholds, and publishes standardized categories atomically for consistent downstream feature computation.

## References
* User Story: **US-20: Standardize POI categories across sources**
* Use Case: `Use Cases/UC-20.md`
* Scenario: `Scenarios/SC-UC-20.md`
* Related Use Case: `Use Cases/UC-17.md` (POI ingestion and raw category capture)
* Related Use Case: `Use Cases/UC-21.md` (deduplication; separate from categorization)

## Assumptions (minimal)
* Raw POIs are stored with provenance (`source`, `source_id`) and at least one raw category field.
* A canonical taxonomy exists and is versioned (or otherwise identifiable).
* Mapping rules exist (lookup tables/rules engine) and are versioned (or otherwise identifiable).
* Standardization uses staging outputs and an atomic promotion step (swap/rename or versioned view update).
* Governance policy for unmapped labels is configured:
  * **Strict**: block promotion if unmapped/conflicts exceed thresholds, **or**
  * **Permissive**: promote with explicit warnings and `unmapped` flags.

## Test Data Setup
Prepare controlled POI datasets and mapping rules for repeatable tests:
* **P1 (Happy path)**: POIs from ≥2 sources with stable raw categories and complete mappings.
* **P2 (New/unrecognized labels)**: POIs containing raw category labels not present in mappings.
* **P3 (Conflicting mapping)**: Same raw label appears and is (mis)configured to map to different canonical categories.
* **P4 (Multi-field categories)**: Source provides `type` + `subtype` fields requiring precedence rules.
* **P5 (Taxonomy change)**: Taxonomy version changes (rename/split/merge category) requiring reclassification.
* **P6 (Promotion failure)**: Induced DB error/lock/permission failure during promotion.
* Ensure a known last known-good standardized production version exists before each negative test.

## Acceptance Test Suite (Gherkin-style)

### AT-20-01 — End-to-end standardization assigns canonical categories (happy path)
**Given** raw POIs are present for **P1** with raw category fields and provenance  
**And** taxonomy + mapping rules are configured  
**When** the maintainer runs POI category standardization  
**Then** each POI in the standardized output has a canonical category assigned  
**And** the standardized output retains provenance (`source`, `source_id`) and raw category fields  
**And** the run report indicates success and includes run ID and taxonomy/mapping versions.

### AT-20-02 — Traceability: raw categories are preserved alongside canonical categories
**Given** a successful standardization run for **P1**  
**When** a standardized POI record is inspected  
**Then** it includes:
* raw category field(s) as ingested
* canonical category (and subcategory if enabled)
* mapping metadata (rule ID/rationale and mapping version if tracked)
* source provenance fields.

### AT-20-03 — Determinism: same inputs + same versions yield identical canonical assignments
**Given** the same **P1** raw POIs and the same taxonomy/mapping versions  
**When** standardization is run multiple times  
**Then** the canonical category assignments are identical for the same POIs  
**And** the run metadata records distinct run IDs/timestamps while preserving the same taxonomy/mapping version identifiers.

### AT-20-04 — Mapping quality metrics are computed and reported
**Given** a standardization run is executed for **P1**  
**When** QA runs on staging outputs  
**Then** the run report includes:
* mapped % and unmapped %
* top unmapped raw labels with counts by source (if any)
* conflicts detected (if any)
* category distribution summary (optional) and anomaly flags (if enabled).

### AT-20-05 — Unrecognized labels are marked as unmapped and surfaced in the report
**Given** raw POIs for **P2** contain previously unseen raw labels  
**When** standardization runs  
**Then** those POIs are assigned `Unmapped/Other` (or equivalent) per policy  
**And** the run report lists the unmapped labels with counts by source  
**And** unmapped labels are not silently dropped.

### AT-20-06 — Multi-field category precedence rules are applied and auditable
**Given** raw POIs for **P4** contain multiple category fields (e.g., `type` and `subtype`)  
**When** standardization runs  
**Then** the system applies configured precedence rules (e.g., prefer subtype when present)  
**And** the selected raw field(s) and rationale are recorded in mapping metadata (or are derivable from the rule ID).

### AT-20-07 — Conflict detection blocks promotion under strict governance
**Given** mappings for **P3** cause the same raw label to map to multiple canonical categories  
**And** governance policy is **Strict**  
**When** standardization runs  
**Then** QA fails due to conflicts exceeding threshold  
**And** promotion is blocked  
**And** production standardized categories remain on the last known-good version  
**And** the report includes conflicting labels and their competing canonical mappings.

### AT-20-08 — Mapping quality below threshold blocks or warns based on governance policy
**Given** a run produces unmapped rate above threshold (e.g., **P2**)  
**When** QA evaluates mapping quality  
**Then** behavior matches configured governance:
* **Strict**: promotion blocked and production unchanged, **or**
* **Permissive**: promotion proceeds with explicit warnings and `unmapped` flags per POI.  
**And** the run report clearly states which policy was applied.

### AT-20-09 — Reclassification after taxonomy change updates canonical categories without re-downloading POIs
**Given** raw POIs exist and a taxonomy change is introduced (**P5**)  
**When** the maintainer reruns standardization using the new taxonomy/mapping versions  
**Then** canonical categories update accordingly  
**And** raw categories remain unchanged  
**And** production version metadata reflects the new taxonomy/mapping versions.

### AT-20-10 — Atomic promotion: production never sees a partially standardized state
**Given** a successful run passes QA  
**When** promotion occurs  
**Then** standardized category updates become visible atomically (swap/rename or versioned view update)  
**And** downstream readers never see a mixture of old and new standardization versions for the same run.

### AT-20-11 — Promotion failure rolls back cleanly and preserves last known-good standardized categories
**Given** a run passes standardization and QA on staging  
**And** promotion is forced to fail using **P6**  
**When** the system attempts promotion  
**Then** the system reports promotion failure with actionable DB error details  
**And** production standardized categories remain unchanged (last known-good version)  
**And** the run is not recorded as a successful production standardization version.

### AT-20-12 — Downstream compatibility: standardized categories are usable for feature computation
**Given** standardized categories are promoted successfully for **P1**  
**When** a downstream query requests POIs by canonical category (e.g., `park`, `school`)  
**Then** results are returned consistently across sources  
**And** there is no need for downstream consumers to interpret source-specific raw labels to compute category-based features.

## Non-Functional Acceptance Criteria (verifiable)
* **Performance**: Standardization completes within an agreed window for target POI volumes.
* **Reliability**: Failures (mapping QA, promotion) do not corrupt production and provide actionable diagnostics.
* **Auditability**: Each run is traceable via run ID and records taxonomy/mapping versions, coverage metrics, conflicts, warnings, and promotion status.
