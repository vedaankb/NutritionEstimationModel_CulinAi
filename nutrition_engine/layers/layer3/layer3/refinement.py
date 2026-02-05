"""
Bounded macro refinement using macro_delta_stats (p10, p90, median, IQR).
Refines initial macros using similar dishes, clamped to percentile bounds.
"""
from __future__ import annotations

from typing import Any

MACRO_KEYS = ["calories", "fat", "carbs", "protein", "sodium"]


def clamp_delta(delta: float, stats: dict[str, float]) -> float:
    """Clamp a relative delta to [p10, p90] from macro_delta_stats."""
    p10 = stats.get("p10", -1.0)
    p90 = stats.get("p90", 1.0)
    return max(p10, min(p90, delta))


def refine_macros(
    initial_macros: dict[str, float],
    similar_dishes: list[dict[str, Any]],
    macro_delta_stats: dict[str, dict],
    *,
    use_median_delta: bool = False,
    weight_by_similarity: bool = True,
) -> dict[str, float]:
    """
    Refine initial_macros using similar dishes. Each neighbor contributes a delta
    (neighbor_macro - initial) / initial, weighted by similarity; delta is clamped to p10–p90.
    If use_median_delta: use macro_delta_stats median only (no neighbors). Else use neighbors.
    """
    refined = {}
    for key in MACRO_KEYS:
        if key not in initial_macros:
            refined[key] = initial_macros.get(key, 0.0)
            continue
        base = initial_macros[key]
        denom = base if abs(base) > 1e-9 else 1.0
        stats = macro_delta_stats.get(key, {})

        if use_median_delta:
            delta = stats.get("median", 0.0)
            delta = clamp_delta(delta, stats)
            refined[key] = base * (1.0 + delta)
            continue

        if not similar_dishes:
            refined[key] = base
            continue

        weighted_delta_sum = 0.0
        weight_sum = 0.0
        for n in similar_dishes:
            sim = n.get("similarity", 0.5)
            neighbor_macros = n.get("macros", n)
            if isinstance(neighbor_macros, dict) and key in neighbor_macros:
                mj = neighbor_macros[key]
            else:
                continue
            delta = (mj - base) / denom
            delta = clamp_delta(delta, stats)
            w = sim if weight_by_similarity else 1.0
            weighted_delta_sum += w * delta
            weight_sum += w
        if weight_sum < 1e-12:
            refined[key] = base
        else:
            avg_delta = weighted_delta_sum / weight_sum
            refined[key] = base * (1.0 + avg_delta)

    return refined


def refine_macros_from_deltas(
    initial_macros: dict[str, float],
    neighbor_list: list[dict[str, Any]],
    macro_delta_stats: dict[str, dict],
    *,
    weight_by_similarity: bool = True,
) -> dict[str, float]:
    """
    Refine using neighbor_list items that have "macro_deltas" and "similarity"
    (e.g. from neighbor_index for a known dish). Clamp each delta to p10–p90.
    """
    refined = {}
    for key in MACRO_KEYS:
        base = initial_macros.get(key, 0.0)
        denom = base if abs(base) > 1e-9 else 1.0
        stats = macro_delta_stats.get(key, {})

        if not neighbor_list:
            refined[key] = base
            continue

        weighted_delta_sum = 0.0
        weight_sum = 0.0
        for n in neighbor_list:
            sim = n.get("similarity", 0.5)
            deltas = n.get("macro_deltas", {})
            if key not in deltas:
                continue
            delta = clamp_delta(deltas[key], stats)
            w = sim if weight_by_similarity else 1.0
            weighted_delta_sum += w * delta
            weight_sum += w
        if weight_sum < 1e-12:
            refined[key] = base
        else:
            avg_delta = weighted_delta_sum / weight_sum
            refined[key] = base * (1.0 + avg_delta)

    return refined
