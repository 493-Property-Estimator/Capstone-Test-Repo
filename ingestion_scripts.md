# Ingestion command examples

Canonical ingestion documentation lives in:

- `docs/INGESTION.md`
- `src/data_sourcing/README.md`

## Common CLI examples

Initialize schema:

```bash
./ingest init-db
```

Ingest a single source by overriding the file path:

```bash
./ingest ingest --source-key geospatial.parks --source 'geospatial.parks=src/data_sourcing/data/Parks_20260320.zip'
```

More examples are in `docs/INGESTION.md`.
