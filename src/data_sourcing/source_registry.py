"""Source registry for local and remote ingestion inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DEFAULT_SOURCE_REGISTRY_PATH


def load_source_registry(path: Path | str | None = None) -> dict[str, Any]:
    registry_path = Path(path) if path else DEFAULT_SOURCE_REGISTRY_PATH
    if not registry_path.exists():
        return {"datasets": {}}
    return json.loads(registry_path.read_text(encoding="utf-8"))


def list_sources(
    path: Path | str | None = None,
    pipeline: str | None = None,
    enabled_only: bool = False,
) -> list[dict[str, Any]]:
    registry = load_source_registry(path)
    datasets = registry.get("datasets", {})
    items: list[dict[str, Any]] = []
    for key, spec in datasets.items():
        if pipeline and spec.get("pipeline") != pipeline:
            continue
        if enabled_only and not bool(spec.get("enabled", True)):
            continue
        items.append({"key": key, **spec})
    return sorted(items, key=lambda item: item["key"])


def get_source_spec(source_key: str, path: Path | str | None = None) -> dict[str, Any]:
    registry = load_source_registry(path)
    spec = registry.get("datasets", {}).get(source_key)
    if not spec:
        raise KeyError(f"source key not found in registry: {source_key}")
    return spec
