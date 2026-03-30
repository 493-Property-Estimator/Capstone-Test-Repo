"""Configuration for local ingestion/refinement pipelines."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
SOURCES_DIR = BASE_DIR / "sources"
DEFAULT_SOURCE_REGISTRY_PATH = SOURCES_DIR / "source_registry.json"
DEFAULT_DB_PATH = BASE_DIR / "open_data.db"

GEOSPATIAL_DATASETS = ("roads", "boundaries", "pois")
TRANSIT_DATASETS = ("stops", "trips")
# GEOSPATIAL_SIZE_LIMIT_BYTES = 5_000_000
GEOSPATIAL_SIZE_LIMIT_BYTES = 2_000_000_000
GEOSPATIAL_MAX_RETRIES = 2
GEOSPATIAL_REPAIR_RATE_LIMIT = 0.20

CENSUS_COVERAGE_THRESHOLD = 0.90

ASSESSMENT_INVALID_RATE_LIMIT = 0.30
ASSESSMENT_UNLINKED_RATE_LIMIT = 0.25
ASSESSMENT_AMBIGUOUS_RATE_LIMIT = 0.40

UNMAPPED_RATE_LIMIT = 0.10
UNMAPPED_POLICY = "warn"  # "warn" or "block"

DEDUPE_AUTO_MERGE_THRESHOLD = 0.85
DEDUPE_REVIEW_THRESHOLD = 0.65
DEDUPE_MAX_DISTANCE_METERS = 250.0

REFRESH_DEPENDENCIES = {
    "geospatial": [],
    "transit": [],
    "census": ["geospatial"],
    "crime": [],
    "assessments": ["geospatial"],
    "poi_standardization": ["geospatial"],
    "deduplication": ["poi_standardization"],
}

REFRESH_MAX_RETRIES = 1
REFRESH_BACKOFF_SECONDS = 0.1
