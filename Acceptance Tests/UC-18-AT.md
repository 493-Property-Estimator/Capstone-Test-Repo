# Acceptance Tests — UC-18: Ingest municipal census datasets

## Purpose
Verify that the system can ingest municipal census datasets, normalize them into canonical schemas, link census geographies to internal neighbourhood (area) keys, compute neighbourhood indicators, run QA/coverage checks, and publish indicators atomically with full provenance and traceability. Verify safe handling of suppression/rounding, boundary/key mismatches, computation failures, coverage shortfalls, and promotion failures.

## References
* User Story: **US-18: Ingest municipal census datasets**
* Use Case: `Use Cases/UC-18.md`
* Scenario: `Scenarios/SC-UC-18.md`
* Related Use Case: `Use Cases/UC-12.md` (neighbourhood indicators consumption)
* Related Use Case: `Use Cases/UC-17.md` (boundaries ingestion; used for linking when applicable)

## Assumptions (minimal)
* Census ingestion is runnable manually (CLI/UI) and optionally via scheduler.
* The pipeline uses staging tables and a promotion mechanism (swap/rename or versioned views) to publish indicators atomically.
* The system records run metadata (run ID, census year, geography level, boundary vintage, coverage, counts, warnings, QA outcomes).
* Suppressed/rounded values are represented explicitly (e.g., null + flags) and never treated as real zeros.

## Test Data Setup
Prepare controlled sources and environments for repeatable tests:
* **C1 (Happy path)**: Valid census artifacts with required fields and stable geography keys; linking coverage above threshold.
* **C2 (Suppression/rounding)**: Artifacts containing suppressed/rounded values for at least one indicator input field.
* **C3 (Schema change)**: Artifact missing required columns or with renamed columns.
* **C4 (Invalid values)**: Artifact with negative counts, invalid codes, or null required keys.
* **C5 (Boundary/key mismatch)**: Geography keys do not match internal boundaries without a complete mapping table.
* **C6 (Computation failure)**: Crafted data to trigger indicator computation errors (division by zero, missing derived prerequisites).
* **C7 (Coverage below threshold)**: Valid artifacts but join coverage intentionally below configured threshold.
* **C8 (Promotion failure)**: Induced DB error/lock/permission failure during promotion.
* Ensure a known last known-good production indicator version exists before each negative test.

## Acceptance Test Suite (Gherkin-style)

### AT-18-01 — End-to-end census ingest success and indicator publication
**Given** the maintainer initiates census ingestion using **C1**  
**When** the pipeline completes  
**Then** the system reports success  
**And** raw census tables are loaded into production (or retained as versioned raw tables) according to policy  
**And** computed neighbourhood indicators are present in production tables/views  
**And** run metadata is recorded with run ID, timestamps, census year, geography level, counts, coverage, and warnings.

### AT-18-02 — Provenance and versioning metadata is captured and inspectable
**Given** a successful run using **C1**  
**When** the maintainer inspects the run report/metadata  
**Then** the report includes:
* census collection year and refresh/publish date (when available)
* geography level
* source/provider and license/attribution note (when available)
* boundary vintage used for linking (or explicit note if not applicable)
* indicator definition/mapping version (if tracked)

### AT-18-03 — Artifact validation: missing required columns blocks publication (schema validation)
**Given** ingestion is started with **C3** (missing/renamed required columns)  
**When** the validator runs  
**Then** the run fails with actionable details listing missing/changed fields  
**And** indicator computation and promotion do not proceed  
**And** the last known-good production indicators remain unchanged.

### AT-18-04 — Value constraints: invalid counts/codes are detected and handled per policy
**Given** ingestion is started with **C4** (invalid values such as negative counts or invalid codes)  
**When** validation runs  
**Then** the system fails the run (or quarantines invalid records) according to configured policy  
**And** the run report includes counts of invalid/rejected/quarantined records and reasons  
**And** the system does not promote inconsistent indicators to production.

### AT-18-05 — Normalization produces canonical schemas with explicit null handling
**Given** ingestion is started with **C1**  
**When** normalization completes  
**Then** canonical column names and types are applied consistently  
**And** missing values are represented explicitly (nulls or configured sentinel strategy)  
**And** required keys are populated for all retained records (or invalid records are quarantined with reporting).

### AT-18-06 — Geography linking: census records map to internal area keys with measurable coverage
**Given** a run using **C1**  
**When** linking to internal neighbourhood/area keys is performed  
**Then** the system produces a link coverage metric (percentage of areas/records mapped)  
**And** coverage is recorded in run metadata  
**And** the run passes only if coverage meets the configured threshold.

### AT-18-07 — Boundary/key mismatch blocks promotion when mapping is incomplete
**Given** ingestion is started with **C5** (geography keys do not match boundaries and mapping table is incomplete)  
**When** linking runs  
**Then** the system reports uncovered areas/keys and coverage below threshold  
**And** promotion is blocked  
**And** last known-good production indicators remain intact.

### AT-18-08 — Suppressed/rounded values are preserved as nulls and flagged (not zero)
**Given** ingestion is started with **C2** containing suppressed/rounded values  
**When** normalization and indicator computation run  
**Then** suppressed inputs are represented as nulls with suppression flags (or equivalent)  
**And** computed indicators impacted by suppression are flagged as limited accuracy (or equivalent)  
**And** the system does not treat suppression as zero or silently drop the issue.

### AT-18-09 — Indicator computation produces required indicators with valid ranges
**Given** a run using **C1**  
**When** indicators are computed  
**Then** all required indicators are present for covered areas  
**And** indicator values satisfy basic constraints (e.g., no negative densities; percentages in [0,100] when applicable)  
**And** indicator units/metadata are consistent with configuration.

### AT-18-10 — Computation failure prevents publication and preserves prior production version
**Given** ingestion is started with **C6** that triggers computation errors  
**When** indicator computation runs  
**Then** the system stops the run and reports which indicator(s) failed and why  
**And** promotion does not occur  
**And** the last known-good production indicators remain unchanged.

### AT-18-11 — Coverage below threshold blocks promotion with actionable report
**Given** ingestion is started with **C7** where join coverage is below threshold  
**When** QA runs  
**Then** QA fails with a coverage error  
**And** the run report identifies which areas/keys are missing and likely cause (linking vs suppression)  
**And** promotion is blocked and prior production indicators remain in place.

### AT-18-12 — Atomic promotion: production indicators update as one consistent version
**Given** a successful run using **C1**  
**When** promotion occurs  
**Then** production indicators update atomically (swap/rename or versioned view update)  
**And** downstream queries never see partially updated indicator tables  
**And** the production version metadata references the run ID and census year/version.

### AT-18-13 — Promotion failure rolls back cleanly and preserves last known-good indicators
**Given** ingestion passes validation, linking, computation, and QA on staging  
**And** promotion is forced to fail using **C8** (DB error/lock/permissions)  
**When** the system attempts promotion  
**Then** the system reports promotion failure with actionable DB error details  
**And** production indicator tables/views remain on the last known-good version  
**And** the run is not recorded as a successful production version.

### AT-18-14 — Scheduled ingestion run behaves like manual run (if scheduler enabled)
**Given** the scheduler is enabled and configured to run UC-18 ingestion  
**When** a scheduled run starts  
**Then** the system produces the same run metadata (run ID, config snapshot, coverage, QA outcomes) as a manual run  
**And** success/failure is emitted to monitoring/alerts according to configuration.

### AT-18-15 — Repeatability: fixed sources/config yield consistent indicators for fixed versions
**Given** ingestion is run multiple times against the same **C1** artifacts and configuration  
**When** runs complete successfully  
**Then** indicator outputs are consistent within defined tolerances/rounding rules  
**And** run metadata records distinct run IDs/timestamps while preserving the same census year/version fields.

## Non-Functional Acceptance Criteria (verifiable)
* **Performance**: Ingestion + indicator computation completes within an agreed window for target dataset sizes.
* **Reliability**: Failures (download/validation/linking/computation/QA/promotion) are detected and reported without corrupting production.
* **Auditability**: Every run is traceable by run ID and records provenance, coverage metrics, warnings, QA outcomes, and promotion status.
