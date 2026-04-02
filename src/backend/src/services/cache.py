from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    dataset_version: str | None


class MemoryCache:
    def __init__(self, ttl_seconds: int):
        self._ttl = ttl_seconds
        self._store: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str, dataset_version: str | None):
        entry = self._store.get(key)
        now = time.time()
        if not entry:
            self.misses += 1
            return None, "miss"
        if entry.expires_at < now:
            self._store.pop(key, None)
            self.misses += 1
            return None, "stale"
        if dataset_version and entry.dataset_version and entry.dataset_version != dataset_version:
            self._store.pop(key, None)
            self.misses += 1
            return None, "stale"
        self.hits += 1
        return entry.value, "hit"

    def set(self, key: str, value: Any, dataset_version: str | None):
        expires_at = time.time() + self._ttl
        self._store[key] = CacheEntry(value=value, expires_at=expires_at, dataset_version=dataset_version)

    def ratio(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total
