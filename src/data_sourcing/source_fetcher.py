"""Resolve and fetch source payloads using configured ingestion techniques."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from .config import REPO_ROOT, SOURCES_DIR
from .source_loader import SourcePayload, load_json_source
from .source_registry import get_source_spec


def _bbox_intersects(
    source_bbox: tuple[float, float, float, float],
    target_bbox: tuple[float, float, float, float],
) -> bool:
    s_minx, s_miny, s_maxx, s_maxy = source_bbox
    t_minx, t_miny, t_maxx, t_maxy = target_bbox
    return not (s_maxx < t_minx or s_minx > t_maxx or s_maxy < t_miny or s_miny > t_maxy)


def _passes_attribute_filters(record: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    for field, expected in filters.items():
        if str(record.get(field)) != str(expected):
            return False
    return True


def _passes_point_bbox_filter(record: dict[str, Any], bbox: tuple[float, float, float, float] | None) -> bool:
    if not bbox:
        return True
    if "lon" not in record or "lat" not in record:
        return False
    min_lon, min_lat, max_lon, max_lat = bbox
    lon = float(record["lon"])
    lat = float(record["lat"])
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def _safe_cache_name(source_key: str, seed: str, ext: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-zA-Z0-9._-]", "_", source_key)
    return f"{slug}_{digest}{ext}"


def _resolve_local_path(local_path: str) -> Path:
    candidate = Path(local_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    repo_candidate = (REPO_ROOT / local_path).resolve()
    if repo_candidate.exists():
        return repo_candidate

    sources_candidate = (SOURCES_DIR / local_path).resolve()
    if sources_candidate.exists():
        return sources_candidate

    raise FileNotFoundError(f"local source file not found: {local_path}")


def _fetch_remote_file(url: str, source_key: str, forced_ext: str | None = None) -> Path:
    cache_dir = SOURCES_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(url)
    guessed_ext = Path(parsed.path).suffix.lower() or ".dat"
    ext = forced_ext if forced_ext else guessed_ext
    cache_path = cache_dir / _safe_cache_name(source_key, url, ext)

    with urlopen(url, timeout=30) as response:
        body = response.read()
    cache_path.write_bytes(body)
    return cache_path


def _normalize_field_name(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _lookup_mapped_value(record: dict[str, Any], source_field: str) -> Any:
    if source_field in record:
        return record[source_field]

    normalized_source = _normalize_field_name(source_field)
    if not normalized_source:
        return None

    normalized_record_keys = {
        _normalize_field_name(key): key
        for key in record
        if isinstance(key, str)
    }
    exact = normalized_record_keys.get(normalized_source)
    if exact is not None:
        return record[exact]

    for normalized_key, original_key in normalized_record_keys.items():
        if not normalized_key:
            continue
        if normalized_key.startswith(normalized_source) or normalized_source.startswith(normalized_key):
            return record[original_key]

    return None


def _apply_field_map(record: dict[str, Any], field_map: dict[str, str] | None) -> dict[str, Any]:
    if not field_map:
        return dict(record)
    normalized = dict(record)
    for target_field, source_field in field_map.items():
        if isinstance(source_field, str) and source_field.startswith("="):
            normalized[target_field] = source_field[1:]
            continue
        if isinstance(source_field, str):
            mapped_value = _lookup_mapped_value(record, source_field)
            if mapped_value is not None:
                normalized[target_field] = mapped_value
    return normalized


def _infer_local_ingestion_technique(source_path: Path, configured_technique: str) -> str:
    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        return "local_csv"
    if suffix in {".json"}:
        return "local_json"
    if suffix in {".geojson"}:
        return "local_geojson"
    if suffix in {".zip", ".shp"}:
        return "local_shapefile"
    return configured_technique


def _normalize_json(path: Path, field_map: dict[str, str] | None) -> SourcePayload:
    payload = load_json_source(path)
    payload.records = [_apply_field_map(row, field_map) for row in payload.records]
    return payload


def _normalize_csv(path: Path, field_map: dict[str, str] | None, spec: dict[str, Any]) -> SourcePayload:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    bbox_raw = spec.get("spatial_filter", {}).get("bbox")
    bbox = tuple(bbox_raw) if isinstance(bbox_raw, list) and len(bbox_raw) == 4 else None
    attr_filters = spec.get("attribute_filters")

    records: list[dict[str, Any]] = []
    dropped = 0
    for row in reader:
        normalized = _apply_field_map(dict(row), field_map)
        if not _passes_attribute_filters(normalized, attr_filters):
            dropped += 1
            continue
        if not _passes_point_bbox_filter(normalized, bbox):
            dropped += 1
            continue
        records.append(normalized)

    metadata = {
        "ingested_from": "csv",
        "source_name": path.name,
        "row_count": len(records),
        "dropped_by_filters": dropped,
    }
    return SourcePayload(
        metadata=metadata,
        records=records,
        size_bytes=len(raw),
        checksum=hashlib.sha256(raw).hexdigest(),
    )


def _normalize_geojson(path: Path, field_map: dict[str, str] | None, spec: dict[str, Any]) -> SourcePayload:
    raw = path.read_bytes()
    parsed = json.loads(raw.decode("utf-8"))
    features = parsed.get("features", [])

    bbox_raw = spec.get("spatial_filter", {}).get("bbox")
    bbox = tuple(bbox_raw) if isinstance(bbox_raw, list) and len(bbox_raw) == 4 else None
    attr_filters = spec.get("attribute_filters")

    records: list[dict[str, Any]] = []
    dropped = 0
    for feature in features:
        props = feature.get("properties", {}) or {}
        geom = feature.get("geometry", {}) or {}
        record = dict(props)
        geom_type = geom.get("type")
        if geom_type == "Point":
            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                record["lon"] = coords[0]
                record["lat"] = coords[1]
                record["geometry_points"] = [[coords[0], coords[1]]]
        elif geom_type == "LineString":
            coords = geom.get("coordinates", [])
            if coords:
                record["geometry_points"] = [[c[0], c[1]] for c in coords if isinstance(c, list) and len(c) >= 2]
        elif geom_type == "MultiLineString":
            coords = geom.get("coordinates", [])
            flattened: list[list[float]] = []
            for line in coords:
                if not isinstance(line, list):
                    continue
                for point in line:
                    if isinstance(point, list) and len(point) >= 2:
                        flattened.append([point[0], point[1]])
            if flattened:
                record["geometry_points"] = flattened

        normalized = _apply_field_map(record, field_map)
        if not _passes_attribute_filters(normalized, attr_filters):
            dropped += 1
            continue
        if not _passes_point_bbox_filter(normalized, bbox):
            dropped += 1
            continue
        records.append(normalized)

    metadata = {
        "ingested_from": "geojson",
        "source_name": path.name,
        "feature_count": len(features),
        "row_count": len(records),
        "dropped_by_filters": dropped,
    }
    return SourcePayload(
        metadata=metadata,
        records=records,
        size_bytes=len(raw),
        checksum=hashlib.sha256(raw).hexdigest(),
    )


def _normalize_arcgis(path: Path, field_map: dict[str, str] | None, spec: dict[str, Any]) -> SourcePayload:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    features = parsed.get("features", [])

    bbox_raw = spec.get("spatial_filter", {}).get("bbox")
    bbox = tuple(bbox_raw) if isinstance(bbox_raw, list) and len(bbox_raw) == 4 else None
    attr_filters = spec.get("attribute_filters")

    records: list[dict[str, Any]] = []
    dropped = 0
    for feature in features:
        attrs = feature.get("attributes", {}) or {}
        geom = feature.get("geometry", {}) or {}
        record = dict(attrs)
        if "x" in geom and "y" in geom:
            record["lon"] = geom.get("x")
            record["lat"] = geom.get("y")

        normalized = _apply_field_map(record, field_map)
        if not _passes_attribute_filters(normalized, attr_filters):
            dropped += 1
            continue
        if not _passes_point_bbox_filter(normalized, bbox):
            dropped += 1
            continue
        records.append(normalized)

    normalized = {
        "metadata": {
            "source_name": parsed.get("displayFieldName", "arcgis"),
            "version": parsed.get("currentVersion"),
            "raw_feature_count": len(features),
            "row_count": len(records),
            "dropped_by_filters": dropped,
            "ingested_from": "arcgis_rest_json",
        },
        "records": records,
    }
    cache_path = path.with_name(path.stem + "_normalized.json")
    cache_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    return load_json_source(cache_path)


def _normalize_shapefile(path: Path, field_map: dict[str, str] | None, spec: dict[str, Any]) -> SourcePayload:
    try:
        import shapefile  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "shapefile ingestion requires the 'pyshp' package (import name: shapefile)"
        ) from exc

    shp_path = path
    if path.suffix.lower() == ".zip":
        temp_dir = SOURCES_DIR / "cache" / f"shp_{path.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "r") as zf:
            zf.extractall(temp_dir)
        requested_layer = spec.get("shapefile_layer")
        shp_candidates = list(temp_dir.rglob("*.shp"))
        if not shp_candidates:
            raise FileNotFoundError("zip archive does not contain .shp file")
        if requested_layer:
            requested_name = str(requested_layer).lower().removesuffix(".shp")
            matched = [candidate for candidate in shp_candidates if candidate.stem.lower() == requested_name]
            if not matched:
                raise FileNotFoundError(
                    f"zip archive does not contain requested shapefile layer '{requested_layer}'"
                )
            shp_path = matched[0]
        else:
            shp_path = shp_candidates[0]

    reader = shapefile.Reader(str(shp_path))
    field_names = [field[0] for field in reader.fields[1:]]

    bbox_raw = spec.get("spatial_filter", {}).get("bbox")
    target_bbox = tuple(bbox_raw) if isinstance(bbox_raw, list) and len(bbox_raw) == 4 else None
    attr_filters = spec.get("attribute_filters")

    records: list[dict[str, Any]] = []
    dropped = 0
    for sr in reader.iterShapeRecords():
        attrs = dict(zip(field_names, sr.record))
        if sr.shape.points:
            x, y = sr.shape.points[0]
            attrs.setdefault("lon", x)
            attrs.setdefault("lat", y)
            attrs.setdefault("geometry_points", [[pt[0], pt[1]] for pt in sr.shape.points])

        if target_bbox and hasattr(sr.shape, "bbox") and sr.shape.bbox:
            shp_bbox = tuple(sr.shape.bbox)  # xmin, ymin, xmax, ymax
            if not _bbox_intersects(shp_bbox, target_bbox):
                dropped += 1
                continue

        normalized = _apply_field_map(attrs, field_map)
        if not _passes_attribute_filters(normalized, attr_filters):
            dropped += 1
            continue
        records.append(normalized)

    raw = path.read_bytes()
    metadata = {
        "ingested_from": "shapefile",
        "source_name": path.name,
        "record_count": len(records),
        "dropped_by_filters": dropped,
        "spatial_filter_bbox": list(target_bbox) if target_bbox else None,
    }
    return SourcePayload(
        metadata=metadata,
        records=records,
        size_bytes=len(raw),
        checksum=hashlib.sha256(raw).hexdigest(),
    )


def resolve_source_location(
    source_key: str,
    overrides: dict[str, str] | None = None,
    registry_path: str | Path | None = None,
) -> tuple[str, str]:
    spec = get_source_spec(source_key, registry_path)
    override = (overrides or {}).get(source_key)
    if override:
        if override.startswith("http://") or override.startswith("https://"):
            return "remote", override
        return "local", str(_resolve_local_path(override))

    technique = spec.get("ingestion_technique", "local_json")
    if technique.startswith("local_"):
        return "local", str(_resolve_local_path(spec["local_path"]))
    if technique.startswith("remote_") or technique == "arcgis_rest_json":
        remote_url = spec.get("remote_url")
        if not remote_url:
            raise ValueError(f"source {source_key} missing remote_url")
        return "remote", remote_url
    raise ValueError(f"unsupported ingestion technique for {source_key}: {technique}")


def load_payload_for_source(
    source_key: str,
    overrides: dict[str, str] | None = None,
    registry_path: str | Path | None = None,
) -> SourcePayload:
    spec = get_source_spec(source_key, registry_path)
    field_map = spec.get("field_map")
    technique = spec.get("ingestion_technique", "local_json")

    location_kind, location = resolve_source_location(source_key, overrides, registry_path)
    if location_kind == "remote":
        forced_ext = None
        if technique in {"remote_csv"}:
            forced_ext = ".csv"
        elif technique in {"remote_geojson"}:
            forced_ext = ".geojson"
        elif technique in {"remote_json", "arcgis_rest_json"}:
            forced_ext = ".json"
        elif technique in {"remote_shapefile"}:
            forced_ext = ".zip"
        source_path = _fetch_remote_file(location, source_key, forced_ext=forced_ext)
    else:
        source_path = Path(location)
        technique = _infer_local_ingestion_technique(source_path, technique)

    if technique in {"local_json", "remote_json"}:
        return _normalize_json(source_path, field_map)
    if technique in {"local_csv", "remote_csv"}:
        return _normalize_csv(source_path, field_map, spec)
    if technique in {"local_geojson", "remote_geojson"}:
        return _normalize_geojson(source_path, field_map, spec)
    if technique in {"local_shapefile", "remote_shapefile"}:
        return _normalize_shapefile(source_path, field_map, spec)
    if technique == "arcgis_rest_json":
        return _normalize_arcgis(source_path, field_map, spec)

    raise ValueError(f"unsupported ingestion technique for {source_key}: {technique}")
