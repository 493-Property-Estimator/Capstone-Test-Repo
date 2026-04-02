from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Metrics:
    request_count: int = 0
    error_count: int = 0
    cache_hit_ratio: float = 0.0
    routing_fallback_usage: int = 0
    avg_latency_ms: float = 0.0
    valuation_time_ms: float = 0.0

    _latency_total_ms: float = 0.0
    _valuation_total_ms: float = 0.0

    def record_request(self, latency_ms: float, is_error: bool = False):
        self.request_count += 1
        if is_error:
            self.error_count += 1
        self._latency_total_ms += latency_ms
        self.avg_latency_ms = self._latency_total_ms / max(self.request_count, 1)

    def record_valuation(self, valuation_ms: float):
        self._valuation_total_ms += valuation_ms
        count = max(self.request_count, 1)
        self.valuation_time_ms = self._valuation_total_ms / count

    def record_routing_fallback(self):
        self.routing_fallback_usage += 1
