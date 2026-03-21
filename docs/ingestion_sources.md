# Source Registry and Ingestion Techniques

Source definitions live in:

- `src/data_sourcing/sources/source_registry.json`

## Supported ingestion techniques

- `local_json`: read deterministic local JSON snapshots.
- `remote_json`: download JSON from HTTP/HTTPS endpoint.
- `local_csv` / `remote_csv`: parse CSV records.
- `local_geojson` / `remote_geojson`: parse GeoJSON `features`.
- `local_shapefile` / `remote_shapefile`: parse Shapefile (`.shp` or zipped shapefile `.zip`); requires `pyshp`.
- `arcgis_rest_json`: download ArcGIS REST JSON and normalize `features`.

## Edmonton source workflow

1. Add/update a source entry in `source_registry.json`.
2. Set `pipeline` for how it should be interpreted and processed.
3. Set `ingestion_technique` and location (`local_path` or `remote_url`).
4. Optionally add `field_map` when source columns differ from expected canonical fields.
5. Optionally add `spatial_filter.bbox` to clip large regional datasets (e.g., Alberta -> Edmonton).
6. Optionally add `attribute_filters` to keep only matching records.
7. Add `downstream_pipelines` when source updates require follow-up processing.
8. Set `enabled: true` once ready for default ingestion runs.
9. Run `./ingest list-sources` to verify config.
10. Run ingest:
   - all sources: `./ingest ingest`
   - targeted sources: `./ingest ingest --source-key <source_key>`

## Failure handling behavior

When `./ingest ingest` runs:

1. Each requested source is pre-checked individually.
2. If one source path is missing, directory is invalid, or URL fetch fails:
   - the error is recorded in DB (`source_checks`) and alerts,
   - the CLI output includes the source-level error,
   - ingestion continues with the next source.
3. Pipelines run only for sources that passed checks.

## Override examples

- `./ingest ingest --source-key geospatial.roads --source geospatial.roads=/data/edmonton_roads.json`
- `./ingest ingest --source-key geospatial.pois --source geospatial.pois=https://example.com/pois.json`
- `./ingest ingest --source-key geospatial.osm_alberta --source geospatial.osm_alberta=/data/osm/alberta-latest-free.shp.zip`
