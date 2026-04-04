# Backend + Frontend Quickstart

## 1. Backend

From repo root:

```bash
pip install -r src/backend/requirements.txt
export DATA_DB_PATH=src/data_sourcing/open_data.db
uvicorn backend.src.app:app --reload --port 8000
```

Optional: if you generated a sample DB

```bash
export DATA_DB_PATH=/tmp/open_data_sample.db
```

## 2. Frontend

From repo root:

```bash
cd src/frontend
python3 -m http.server 8080
```

Open:

```
http://localhost:8080
```

## 3. Notes

- CORS is enabled for `http://localhost:8080`.
- The frontend expects the backend at `http://localhost:8000/api/v1`.
- If the backend cannot find data, run ingestion or generate a sample DB.
