"""
Confidence from similarity, variance penalty, and ingredient coverage (lookup only).
"""
from __future__ import annotations

import numpy as np


def similarity_to_confidence(
    similarity: float,
    bin_edges: list[float],
    confidence_at_bin: list[float],
) -> float:
    """Interpolate confidence from similarity using bin_edges and confidence_at_bin."""
    if not bin_edges or not confidence_at_bin:
        return 0.5
    bins = np.array(bin_edges)
    vals = np.array(confidence_at_bin)
    if similarity <= bins[0]:
        return float(vals[0])
    if similarity >= bins[-1]:
        return float(vals[-1])
    return float(np.interp(similarity, bins, vals))


def coverage_penalty(
    coverage: float,
    bins: list[float],
    penalties: list[float],
) -> float:
    """Interpolate penalty from ingredient coverage (0 = no penalty, 1 = max penalty when coverage low)."""
    if not bins or not penalties:
        return 0.0
    return float(np.interp(coverage, bins, penalties))


def compute_confidence(
    similarity: float,
    ingredient_coverage: float,
    confidence_params: dict,
) -> float:
    """
    Base confidence from similarity (via lookup), then reduce by coverage penalty.
    Returns value in [0, 1].
    """
    stc = confidence_params.get("similarity_to_confidence", {})
    base = similarity_to_confidence(
        similarity,
        stc.get("bin_edges", [0, 1]),
        stc.get("confidence_at_bin", [0.5, 1.0]),
    )
    bins = confidence_params.get("ingredient_coverage_bins", [0.0, 0.5, 0.75, 1.0])
    penalties = confidence_params.get("ingredient_coverage_penalty", [0.5, 0.2, 0.05, 0.0])
    pen = coverage_penalty(ingredient_coverage, bins, penalties)
    return max(0.0, min(1.0, base - pen))


def ingredient_coverage(ingredients: list[str], known_ingredients: set[str]) -> float:
    """Fraction of ingredients that appear in known_ingredients (e.g. embedding keys)."""
    if not ingredients:
        return 1.0
    ings = {str(x).strip().lower() for x in ingredients}
    known = {str(x).strip().lower() for x in known_ingredients}
    return sum(1 for i in ings if i in known) / len(ings)
