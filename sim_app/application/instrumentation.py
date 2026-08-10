"""Small structured metrics hook for persistence and transition operations."""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from contextlib import contextmanager


class OperationMetrics:
    def __init__(self, logger=None):
        self._logger = logger or logging.getLogger("sim_app.operations")
        self._counters = Counter()
        self._latencies = Counter()
        self._lock = threading.Lock()

    @contextmanager
    def measure(self, operation, *, layer="application"):
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            with self._lock:
                self._counters[f"{layer}.{operation}.count"] += 1
                self._latencies[f"{layer}.{operation}.latency_ms"] += elapsed_ms
            self._logger.info(
                "experiment_operation",
                extra={"operation": operation, "layer": layer, "latency_ms": round(elapsed_ms, 3)},
            )

    def increment(self, metric, amount=1):
        with self._lock:
            self._counters[metric] += amount

    def snapshot(self):
        with self._lock:
            return {**dict(self._counters), **dict(self._latencies)}


DEFAULT_METRICS = OperationMetrics()


__all__ = ["DEFAULT_METRICS", "OperationMetrics"]
