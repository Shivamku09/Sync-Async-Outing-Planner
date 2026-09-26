from __future__ import annotations

from math import ceil


def percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, ceil(percentage * len(ordered)))
    return round(ordered[rank - 1], 2)


def latency_summary(values_ms: list[float]) -> dict[str, float | None]:
    return {
        "p50": percentile(values_ms, 0.50),
        "p95": percentile(values_ms, 0.95),
        "p99": percentile(values_ms, 0.99),
    }
