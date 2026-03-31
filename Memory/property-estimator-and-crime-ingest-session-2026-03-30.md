# Property Estimator And Crime Ingest Session

Date: 2026-03-30

## Summary

This session added a production-style baseline-anchored property estimator to the repository, integrated it into TestingStage, and then added a first-pass official crime summary ingestion path using Statistics Canada data filtered to Edmonton.

## Property Estimator Work

- Implemented a new estimator pipeline in `src/estimator/property_estimator.py`.
- Extended `src/estimator/proximity.py` for:
  - nearest libraries
  - neighbourhood aggregate lookups
  - downtown Edmonton accessibility
  - comparable grouping by supplied attributes
- Exported the new estimator surface from `src/estimator/__init__.py`.
- Integrated the estimator into:
  - `TestingStage/backend/services.py`
  - `TestingStage/backend/server.py`
- Added a TestingStage estimator page:
  - `TestingStage/frontend/estimator.html`
  - `TestingStage/frontend/estimator-page.js`
- Added estimator test coverage in `tests/test_property_estimator.py`.

## Estimator Behavior Implemented

- Baseline anchored to `property_locations_prod` / `assessments_prod`.
- Supports point-only estimation and optional later property attributes.
- Returns:
  - final estimate
  - low/high range
  - baseline metadata
  - top positive/negative contributing factors
  - confidence and completeness
  - warnings, missing factors, fallback flags
  - comparables split into matching / non-matching groups
  - neighbourhood context
  - matched-property assessed vs estimated delta where applicable
- Reuses TestingStage road/transit helpers and preserves straight-line fallback behavior.
- Explicitly handles missing datasets instead of fabricating values.

## Data Reality Confirmed During Work

- `census_prod` exists but had `0` rows.
- No `crime_*` tables existed initially.
- Libraries were only realistically discoverable through POI data.
- Transit data exists, but generic transit travel time is not broadly usable as a reliable estimator feature.

## Crime Source Decision

The user asked how to get crime data into the DB and into the “ingest all” flow. After reviewing source options:

- EPS community safety portal was judged possible but too fragile / unclear for first production ingest.
- Alberta municipality crime file was judged too coarse and stale.
- Statistics Canada table `35-10-0183-01` was chosen as the best first official source.

Important limitation:

- The StatsCan source is Edmonton municipal / city-level summary data, not neighbourhood incident data.
- It improves the repository from “no crime data” to “official coarse crime summary data,” but does not satisfy neighbourhood-level crime requirements by itself.

## Crime Ingest Implementation

Added new schema in `src/data_sourcing/database.py`:

- `crime_summary_staging`
- `crime_summary_prod`

Added new pipeline wiring:

- `src/data_sourcing/pipelines.py`
  - new `run_crime_ingest(...)`
- `src/data_sourcing/service.py`
  - new `crime` pipeline registration

Added source config:

- `src/data_sourcing/sources/source_registry.json`
  - `crime.statscan_police_service`

Added auto-discovery support:

- `scripts/ingest_data_folder.py`

Adjusted backend crime availability detection:

- `TestingStage/backend/services.py`
  - empty crime tables no longer count as “available”

Added tests:

- `tests/test_crime_ingest.py`

## Official Crime Source Used

Official StatsCan table:

- `https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510018301`

Direct ZIP used:

- `https://www150.statcan.gc.ca/n1/tbl/csv/35100183-eng.zip`

Downloaded file saved as:

- `src/data_sourcing/data/35100183-eng.zip`

Generated Edmonton-only filtered CSV:

- `src/data_sourcing/data/StatsCan_Police_Service_Crime_Edmonton.csv`

## How The Crime File Was Prepared

The ZIP contains a very large `35100183.csv`. It was filtered to:

- `GEO` containing `Edmonton, Alberta, municipal`
- `Statistics` in:
  - `Actual incidents`
  - `Rate per 100,000 population`

The ingest mapping was adjusted so:

- `Violations` is used as the crime category
- `Statistics` distinguishes count vs rate rows

Blank `VALUE` rows are skipped with a warning instead of failing the whole pipeline.

## Commands Used

Download official ZIP:

```bash
wget --user-agent='Mozilla/5.0' --output-document='src/data_sourcing/data/35100183-eng.zip' 'https://www150.statcan.gc.ca/n1/tbl/csv/35100183-eng.zip'
```

Generate Edmonton-only CSV:

```bash
python3 -c "import csv, zipfile; src='src/data_sourcing/data/35100183-eng.zip'; dst='src/data_sourcing/data/StatsCan_Police_Service_Crime_Edmonton.csv'; allowed_stats={'Actual incidents','Rate per 100,000 population'}; geo_match='Edmonton, Alberta, municipal'; count=0; z=zipfile.ZipFile(src); f=z.open('35100183.csv'); r=csv.DictReader((line.decode('utf-8-sig') for line in f)); fieldnames=r.fieldnames; out=open(dst,'w',newline='',encoding='utf-8'); w=csv.DictWriter(out, fieldnames=fieldnames); w.writeheader(); \
for row in r: \
    if geo_match in row.get('GEO','') and row.get('Statistics') in allowed_stats: \
        w.writerow(row); count += 1; \
out.close(); print(dst); print(count)"
```

Run crime ingest:

```bash
python3 - <<'PY'
from src.data_sourcing.service import IngestionService
service = IngestionService("src/data_sourcing/open_data.db")
print(service.ingest(
    source_keys=["crime.statscan_police_service"],
    source_overrides={
        "crime.statscan_police_service": "src/data_sourcing/data/StatsCan_Police_Service_Crime_Edmonton.csv"
    },
    trigger="manual",
))
PY
```

## Final Crime Ingest Result

- `crime_summary_prod` populated with `6340` rows.
- Year coverage: `1998` to `2024`.
- Warnings indicated skipped rows with blank `VALUE` fields.
- Sample neighbourhood/geography string in stored data:
  - `Edmonton, Alberta, municipal [48033]`

## Test / Verification Results

Passing tests at end of session:

- `python3 -m unittest tests.test_property_estimator`
- `python3 -m unittest tests.test_crime_ingest`
- `python3 -m unittest tests.test_testingstage_services`
- combined reruns passed after final fixes

## Remaining Gaps

- Crime data is still city-level, not neighbourhood-level.
- No incident-point Edmonton crime source has been implemented.
- `census_prod` remains empty.
- No estimator caching layer has been added yet.
- A future improvement would be a dedicated script like `scripts/download_and_prepare_crime_data.py` to automate the StatsCan refresh flow.
