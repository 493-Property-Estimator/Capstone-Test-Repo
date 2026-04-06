# Edmonton neighbourhood census data: recommended sources

Use the City of Edmonton Open Data portal rather than scraping HTML pages.

Core official sources used by the script:
- `eg3i-f4bj` — 2021 Federal Census: Population
- `xgkv-ii9t` — 2021 Federal Census: Households and Families
- `5bk4-5txu` — 2021 Federal Census: Neighbourhoods as of Official Census Day
- `65fr-66s6` — City of Edmonton - Neighbourhoods

Socrata API patterns:
```text
https://data.edmonton.ca/resource/<dataset_id>.json
https://data.edmonton.ca/resource/<dataset_id>.csv
```

Examples:
```text
https://data.edmonton.ca/resource/eg3i-f4bj.csv
https://data.edmonton.ca/resource/xgkv-ii9t.csv
https://data.edmonton.ca/resource/5bk4-5txu.geojson
```

Why this route is better than scraping:
- stable API endpoints
- structured fields
- easier joins by neighbourhood number
- easier refreshes when Edmonton republishes data

## Ingest into this repository DB

Build CSV:

```bash
python scripts/edmonton_neighbourhood_census_builder.py --out edmonton_neighbourhood_census.csv
```

Ingest:

```bash
./ingest ingest \
  --source-key census.neighbourhood_indicators \
  --source census.neighbourhood_indicators=edmonton_neighbourhood_census.csv
```

Verify:

```bash
sqlite3 src/data_sourcing/open_data.db "SELECT COUNT(*) FROM census_prod;"
```

Fallback option:
- The City also links a Tableau-based neighbourhood profiles view with demographic information on population, housing, family mobility status, education, income, and occupation.
- Use that only if you need profile-only attributes that are not exposed as open-data tables.
