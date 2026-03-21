"""Data source loading and simple validation helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SourcePayload:
    metadata: dict[str, Any]
    records: list[dict[str, Any]]
    size_bytes: int
    checksum: str


def load_json_source(path: Path) -> SourcePayload:
    raw = path.read_bytes()
    parsed = json.loads(raw.decode("utf-8"))
    return SourcePayload(
        metadata=parsed.get("metadata", {}),
        records=parsed.get("records", []),
        size_bytes=len(raw),
        checksum=hashlib.sha256(raw).hexdigest(),
    )


def require_fields(record: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    return [field for field in fields if field not in record]
