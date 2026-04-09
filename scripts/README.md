# Scripts

This folder contains developer utilities used for data ingestion, dataset preparation, and verification workflows.

Unless stated otherwise, run scripts from the repo root. Many scripts expose `--help`:

```bash
python3 scripts/<script_name>.py --help
```

## Common prerequisites

- App/backend Python deps:
  - `pip install -r src/backend/requirements.txt`
  - `pip install -r src/backend/requirements-dev.txt`
- Some scripts require extra packages not included in the core app requirements:
  - Playwright-based scripts: `pip install playwright bs4 requests` then `python3 -m playwright install chromium`

## Script index

### Ingestion helpers

- `scripts/ingest_data_folder.py`: auto-discovers known files under `src/data_sourcing/data/` and ingests the latest match per source key.
  - Run: `python3 scripts/ingest_data_folder.py --dry-run`
  - Run: `python3 scripts/ingest_data_folder.py --db src/data_sourcing/open_data.db`

- `scripts/init_and_ingest_open_data.py`: initializes the SQLite schema then runs `scripts/ingest_data_folder.py` for all discovered sources.
  - Run: `python3 scripts/init_and_ingest_open_data.py --dry-run`
  - Run: `python3 scripts/init_and_ingest_open_data.py --db src/data_sourcing/open_data.db`

- `scripts/download_and_prepare_crime_data.py`: downloads the official StatsCan crime ZIP, filters for Edmonton rows, writes a prepared CSV, and can optionally ingest it.
  - Run: `python3 scripts/download_and_prepare_crime_data.py --help`
  - Run: `python3 scripts/download_and_prepare_crime_data.py --ingest --db src/data_sourcing/open_data.db`

### Database utilities

- `scripts/create_db_sample.py`: creates a smaller “sample” SQLite DB by copying a limited number of property/POI rows from a full database.
  - Run: `python3 scripts/create_db_sample.py --output-db /tmp/open_data_sample.db`

### Bed/Bath enrichment prep + validation

- `scripts/run_bedbath_shadow_proof.py`: generates a synthetic DB + inputs, runs bed/bath enrichment in shadow mode, and writes exports under `reports/bedbath_shadow_proof/`.
  - Run: `python3 scripts/run_bedbath_shadow_proof.py`

- `scripts/bed_bath.py`: best-effort automatic REALTOR.ca scraper (Playwright) exporting a per-neighbourhood sample to CSV.
  - Run: `python3 scripts/bed_bath.py`

- `scripts/manual_bed_bath.py`: semi-manual REALTOR.ca map-card scraper that connects to a local browser via the DevTools protocol.
  - Run: `python3 scripts/manual_bed_bath.py --help`

- `scripts/clean_realtor_cards.py`: merges and cleans REALTOR card CSVs, deduplicates by address, and enriches location fields.
  - Run: `python3 scripts/clean_realtor_cards.py --help`

### Census dataset builder

- `scripts/edmonton_neighbourhood_census_builder.py`: pulls official City of Edmonton open data from Socrata and builds a combined “one row per neighbourhood” census CSV.
  - Run: `python3 scripts/edmonton_neighbourhood_census_builder.py --help`
  - Companion notes: `scripts/edmonton_neighbourhood_census_notes.md`

### Test + coverage helper

- `scripts/run_combined_coverage.sh`: runs Python + frontend tests and writes a combined coverage text report under `coverage/combined/`.
  - Run: `bash scripts/run_combined_coverage.sh`
  - Note: enforces `--cov-fail-under=100` for Python coverage.
