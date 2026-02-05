"""
Layer 3: refinement using embeddings and similarity neighborhoods.

Takes input from Layer 1 or Layer 2 (ingredients, cooking methods, sauces, portion, optional macros),
embeds the dish, finds similar dishes, and outputs refined macros with bounded, explainable adjustments.

Usage:
    from layer3 import refine

    result = refine(
        ingredients=["chicken breast", "rice", "broccoli"],
        cooking_methods=["baked", "steamed"],
        sauces=0.2,
        portion_class="medium",
        initial_macros={"calories": 400, "fat": 12, "carbs": 45, "protein": 35, "sodium": 500},
        artifacts_dir=Path("artifacts"),
    )
    # result.refined_macros, result.confidence, result.similar_dish_ids
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from . import confidence as _confidence
from . import embeddings as _embeddings
from . import loader
from . import refinement as _refinement
from . import similarity as _similarity
from . import learned_refinement as _learned_refinement

__version__ = "0.1.0"

DEFAULT_ARTIFACTS_DIR = loader.DEFAULT_ARTIFACTS_DIR
TOP_K_DEFAULT = 7


@dataclass
class RefineInput:
    """Input from Layer 1 or Layer 2."""

    ingredients: list[str]
    cooking_methods: list[str]
    sauces: float
    portion_class: str
    initial_macros: dict[str, float] | None = None
    dish_id: str | None = None  # optional; if provided and in neighbor_index, use neighbors directly


@dataclass
class RefineResult:
    """Output of refine()."""

    refined_macros: dict[str, float]
    confidence: float
    similar_dish_ids: list[str]
    similar_dishes: list[dict[str, Any]]  # full neighbor info (similarity, macros)
    initial_macros_used: dict[str, float]
    embedding: Any  # np.ndarray dish embedding


def refine(
    ingredients: list[str],
    cooking_methods: list[str],
    sauces: float,
    portion_class: str,
    initial_macros: dict[str, float] | None = None,
    dish_id: str | None = None,
    artifacts_dir: Path | None = None,
    artifacts: dict[str, Any] | None = None,
    top_k: int = TOP_K_DEFAULT,
) -> RefineResult:
    """
    Refine macros for a dish using Layer 3 artifacts.

    Input (from Layer 1 or Layer 2):
        ingredients: list of ontology-normalized ingredient names
        cooking_methods: list of ontology-normalized cooking methods
        sauces: scalar 0–1
        portion_class: "small" | "medium" | "large"
        initial_macros: optional {calories, fat, carbs, protein, sodium} from Layer 1/2
        dish_id: optional; if this dish is in the training set, neighbor_index is used

    If initial_macros is None, a default is derived from the mean of top similar dishes
    (so refinement still has a base to adjust).

    Returns:
        RefineResult with refined_macros, confidence, similar_dish_ids, etc.
    """
    if artifacts_dir is None:
        artifacts_dir = DEFAULT_ARTIFACTS_DIR
    if artifacts is None:
        artifacts = loader.load_all(artifacts_dir)

    ing_emb = artifacts["ingredient_embeddings"]
    dish_emb = artifacts["dish_embeddings"]
    neighbor_index = artifacts["neighbor_index"]
    macro_delta_stats = artifacts["macro_delta_stats"]
    confidence_params = artifacts["confidence_params"]

    mean_emb = np.mean(list(ing_emb.values()), axis=0) if ing_emb else None

    query_embedding = _embeddings.embed_dish(
        ingredients,
        cooking_methods,
        sauces,
        portion_class,
        ing_emb,
        mean_embedding=mean_emb,
    )

    # Similar dishes: use neighbor_index if dish_id is known, else top-k by embedding
    similar_dishes: list[dict[str, Any]] = []
    if dish_id and str(dish_id) in neighbor_index:
        similar_dishes = [
            {
                "dish_id": n["neighbor_id"],
                "similarity": n["similarity"],
                "macros": dish_emb.get(n["neighbor_id"], {}).get("macros", {}),
                "macro_deltas": n["macro_deltas"],
            }
            for n in neighbor_index[str(dish_id)]
        ]
    else:
        top = _similarity.top_k_similar(query_embedding, dish_emb, k=top_k)
        similar_dishes = [{"dish_id": t["dish_id"], "similarity": t["similarity"], "macros": t["macros"]} for t in top]

    # Base macros: use initial_macros or mean of similar dishes
    macro_keys = ["calories", "fat", "carbs", "protein", "sodium"]
    if initial_macros and any(initial_macros.get(k) is not None for k in macro_keys):
        base_macros = {k: float(initial_macros.get(k, 0) or 0) for k in macro_keys}
    else:
        if similar_dishes:
            base_macros = {}
            for k in macro_keys:
                vals = [d["macros"].get(k, 0) for d in similar_dishes if isinstance(d.get("macros"), dict)]
                base_macros[k] = sum(vals) / len(vals) if vals else 0.0
        else:
            base_macros = {k: 0.0 for k in macro_keys}

    # Refine: use learned model if present, else rule-based (macro_deltas or neighbor macros)
    learned = _learned_refinement.load_model(artifacts_dir)
    if learned is not None:
        refined = _learned_refinement.predict(
            query_embedding,
            base_macros,
            similar_dishes,
            dish_emb,
            learned,
            macro_delta_stats=macro_delta_stats,
            clamp_to_bounds=True,
        )
    elif similar_dishes and "macro_deltas" in similar_dishes[0]:
        refined = _refinement.refine_macros_from_deltas(
            base_macros,
            [{"similarity": d["similarity"], "macro_deltas": d["macro_deltas"]} for d in similar_dishes],
            macro_delta_stats,
            weight_by_similarity=True,
        )
    else:
        refined = _refinement.refine_macros(
            base_macros,
            similar_dishes,
            macro_delta_stats,
            weight_by_similarity=True,
        )

    # Confidence
    avg_similarity = sum(d["similarity"] for d in similar_dishes) / len(similar_dishes) if similar_dishes else 0.0
    known_ings = set(ing_emb.keys())
    coverage = _confidence.ingredient_coverage(ingredients, known_ings)
    conf = _confidence.compute_confidence(avg_similarity, coverage, confidence_params)

    return RefineResult(
        refined_macros=refined,
        confidence=conf,
        similar_dish_ids=[d["dish_id"] for d in similar_dishes],
        similar_dishes=similar_dishes,
        initial_macros_used=base_macros,
        embedding=query_embedding,
    )


__all__ = [
    "__version__",
    "refine",
    "RefineInput",
    "RefineResult",
    "DEFAULT_ARTIFACTS_DIR",
    "loader",
    "embeddings",
    "similarity",
    "refinement",
    "learned_refinement",
    "confidence",
]
