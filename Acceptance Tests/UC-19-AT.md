# Acceptance Tests — UC-19: Ingest property tax assessment data

## Purpose
Verify that the system can ingest property tax assessment data, validate and normalize key fields (assessment value + identifiers), link records to the system’s canonical location IDs, build fast lookup indexes, run QA checks (coverage, duplicates, outliers, linking quality), and publish the new baseline atomically with provenance/versioning recorded. Verify safe failure behavior that preserves the last known-good baseline.

## References
* User Story: **US-19: Ingest property tax assessment data**
* Use Case: `Use Cases/UC-19.md`
* Scenario: `Scenarios/SC-UC-19.md`
* Related Use Case: `Use Cases/UC-16.md` (baseline used for valuation)
* Related Use Case: `Use Cases/UC-17.md` (parcels/boundaries for spatial linking when applicable)

## Assumptions (minimal)
* Assessment ingestion is runnable manually (CLI/UI) and optionally via scheduler.
* The pipeline uses staging tables and an atomic promotion mechanism (swap/rename or versioned views).
* The system records run metadata (run ID, assessment year, source/publish date, coverage, ambiguous/unlinked rates, counts, warnings, QA outcomes).
* A deterministic strategy exists for resolving duplicates and ambiguous links (auditable tie-break rules).

## Test Data Setup
Prepare controlled sources and environments for repeatable tests:
* **A1 (Happy path)**: Valid assessment artifact for a known year with stable schema and high linking coverage.
* **A2 (Download failure)**: Source URL that times out / returns 5xx / missing file.
* **A3 (Schema change)**: Artifact missing required columns (assessment value, identifier/address) or renamed fields.
* **A4 (Invalid values)**: Artifact with non-numeric currency strings, negative values, or null required keys.
* **A5 (Linking ambiguity)**: Data that yields multiple candidate matches for a subset of records (parcel/address duplicates).
* **A6 (Low linking coverage)**: Data that cannot be linked for many records (missing identifiers or mismatched keys).
* **A7 (Duplicates)**: Data where multiple rows map to the same canonical location ID (condos/multi-unit or duplicate source records).
* **A8 (Outliers)**: Data with extreme values designed to trigger outlier detection.
* **A9 (Promotion failure)**: Induced DB lock/permission failure during promotion.
* Ensure a known last known-good production baseline exists before each negative test.

## Acceptance Test Suite (Gherkin-style)

### AT-19-01 — End-to-end assessment ingest success and baseline availability
**Given** the maintainer initiates assessment ingestion using **A1**  
**When** the pipeline completes  
**Then** the system reports success  
**And** the assessment baseline is queryable in production by canonical location ID  
**And** lookup indexes required for fast retrieval are present/updated (per implementation)  
**And** run metadata is recorded with run ID, assessment year, timestamps, and counts.

### AT-19-02 — Provenance and year/version metadata is captured and inspectable
**Given** a successful run using **A1**  
**When** the maintainer inspects the run report/metadata  
**Then** the report includes:
* assessment year
* publish/refresh date (when available)
* source/provider and license/coverage notes (when available)
* run ID, start/end timestamps
* counts (raw rows, normalized rows, linked rows, unlinked rows)

### AT-19-03 — Schema validation blocks ingestion when required fields are missing
**Given** ingestion is started with **A3** (missing/renamed required columns)  
**When** schema validation runs  
**Then** the run fails with actionable details listing missing/changed fields  
**And** loading/linking/promotion do not proceed  
**And** the last known-good production baseline remains unchanged.

### AT-19-04 — Value validation and normalization: currency parsing and constraints
**Given** ingestion is started with **A4** containing invalid/negative/non-numeric assessment values or null required keys  
**When** validation and normalization run  
**Then** the system fails the run or quarantines invalid records according to policy  
**And** the run report includes counts and reasons for rejected/quarantined rows  
**And** invalid values are not silently coerced into misleading numbers.

### AT-19-05 — Linking to canonical location IDs achieves measured coverage
**Given** ingestion is started with **A1**  
**When** linking runs  
**Then** each retained record is either linked to a canonical location ID or marked unlinked with a reason code  
**And** the system computes linking coverage metrics (linked %, unlinked %, ambiguous %)  
**And** those metrics are recorded in run metadata.

### AT-19-06 — Linking ambiguity is resolved deterministically and flagged
**Given** ingestion is started with **A5** where some records have multiple candidate matches  
**When** the linker resolves matches  
**Then** the system applies deterministic tie-break rules (repeat runs choose the same match for the same inputs)  
**And** ambiguous links are flagged for audit with a link method/confidence indicator  
**And** if ambiguity rate exceeds threshold, QA fails and promotion is blocked.

### AT-19-07 — Low linking coverage blocks promotion (thresholded QA)
**Given** ingestion is started with **A6** producing low linking coverage  
**When** QA runs  
**Then** QA fails with a coverage/linking-quality error  
**And** the run report identifies likely causes (missing identifiers, join mismatch, mapping gaps)  
**And** promotion is blocked and prior production baseline remains intact.

### AT-19-08 — Duplicate mappings are resolved by deterministic rules and are auditable
**Given** ingestion is started with **A7** where multiple records map to the same canonical location ID  
**When** duplicates are detected  
**Then** the system applies a deterministic resolution rule (e.g., highest confidence match; preferred record type; latest year when multiple years ingested)  
**And** the system records the duplicate rate and resolution outcomes in the run report  
**And** the production baseline does not contain conflicting multiple baseline values for the same canonical location ID (unless explicitly versioned and queryable).

### AT-19-09 — Outlier detection flags extreme values and supports safe publication policy
**Given** ingestion is started with **A8** containing extreme high/low assessment values  
**When** QA runs  
**Then** outliers are flagged with counts (and optionally examples/IDs)  
**And** promotion proceeds only if outlier rate is within configured tolerance, otherwise QA fails and blocks promotion  
**And** outlier warnings are recorded in run metadata for audit.

### AT-19-10 — Atomic promotion publishes a consistent baseline version
**Given** a successful run using **A1**  
**When** promotion occurs  
**Then** the baseline is promoted atomically (swap/rename or versioned view update)  
**And** valuation/baseline lookup never observes a partially promoted state  
**And** the production baseline version metadata references the run ID and assessment year.

### AT-19-11 — Promotion failure rolls back cleanly and preserves last known-good baseline
**Given** ingestion passes validation/linking/QA on staging  
**And** promotion is forced to fail using **A9** (DB lock/permissions)  
**When** the system attempts promotion  
**Then** the system reports promotion failure with actionable DB error details  
**And** production baseline remains the last known-good version  
**And** the run is not recorded as a successful production baseline version.

### AT-19-12 — Scheduled assessment ingestion behaves like manual run (if scheduler enabled)
**Given** the scheduler is enabled and configured to run UC-19 ingestion  
**When** a scheduled run starts  
**Then** the system produces the same run metadata (run ID, coverage, QA outcomes) as a manual run  
**And** success/failure is emitted to monitoring/alerts according to configuration.

### AT-19-13 — Repeatability: fixed inputs/config yield consistent linking and baseline outputs
**Given** ingestion is run multiple times against the same **A1** artifact and configuration  
**When** runs complete successfully  
**Then** row counts, linking coverage, and duplicate resolution outcomes are consistent within expected tolerances  
**And** the same canonical location ID receives the same baseline value for a fixed assessment year (within rounding rules)  
**And** distinct run IDs/timestamps are recorded for each run.

## Non-Functional Acceptance Criteria (verifiable)
* **Performance**: Ingestion + linking + index build completes within an agreed window for target dataset sizes.
* **Reliability**: Failures (download/validation/linking/QA/promotion) are detected and reported without corrupting production.
* **Auditability**: Every run is traceable by run ID and records provenance, linking outcomes/coverage, QA results, warnings, and promotion status.
