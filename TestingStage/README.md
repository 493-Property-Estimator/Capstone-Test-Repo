# TestingStage

Simple frontend and backend playground for testing calls against the sample SQLite database.

## What is included

- `backend/server.py`: plain-Python HTTP server with JSON endpoints and static file serving
- `frontend/`: multi-page Leaflet frontend
- `src/estimator/simple_estimator.py`: summary statistics for the nearest 15 properties

## Run

From the repo root:

```bash
python3 TestingStage/backend/server.py
```

Then open `http://127.0.0.1:8010`.

## Endpoints

- `POST /api/nearest-property`
- `POST /api/top-x`
- `POST /api/point-distances`
- `GET /api/neighborhoods`
- `GET /api/neighborhood-summary?name=...`

## Notes

- The map relies on the Leaflet CDN and OpenStreetMap tiles.
- The neighborhood summary uses the selected neighborhood's property bounding box for POI and road metrics because this sample database does not currently expose final neighborhood polygon tables in populated form.
