"""
Learned refinement model: predicts refined macros from (query_embedding, initial_macros, top-k neighbors).
Trained offline; used at inference when artifacts/refinement_model.joblib exists.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

MACRO_KEYS = ["calories", "fat", "carbs", "protein", "sodium"]
TOP_K_NEIGHBORS = 7
QUERY_EMB_DIM = 26  # must match notebook dish embedding dim
FEATURE_DIM = QUERY_EMB_DIM + 5 + TOP_K_NEIGHBORS * (QUERY_EMB_DIM + 5 + 1)  # 255


def build_feature_vector(
    query_embedding: np.ndarray,
    initial_macros: dict[str, float],
    similar_dishes: list[dict[str, Any]],
    dish_embeddings: dict[str, dict],
) -> np.ndarray:
    """
    Build fixed-size feature vector for the refinement model.
    Layout: query_emb (26) + initial_macros (5) + [neighbor_emb (26) + neighbor_macros (5) + sim (1)] * 7.
    Pads with zeros if fewer than 7 neighbors; truncates if more.
    """
    q = np.asarray(query_embedding, dtype=np.float64).ravel()
    if q.size != QUERY_EMB_DIM:
        q = np.resize(q, QUERY_EMB_DIM)
    init = np.array(
        [float(initial_macros.get(k, 0)) for k in MACRO_KEYS],
        dtype=np.float64,
    )
    parts = [q, init]
    for i in range(TOP_K_NEIGHBORS):
        if i < len(similar_dishes):
            d = similar_dishes[i]
            did = d.get("dish_id")
            if did and did in dish_embeddings:
                neb = np.asarray(dish_embeddings[did]["embedding"], dtype=np.float64).ravel()
                neb = np.resize(neb, QUERY_EMB_DIM)
                nm = np.array(
                    [float(d.get("macros", {}).get(k, 0)) for k in MACRO_KEYS],
                    dtype=np.float64,
                )
                sim = float(d.get("similarity", 0))
            else:
                neb = np.zeros(QUERY_EMB_DIM, dtype=np.float64)
                nm = np.zeros(5, dtype=np.float64)
                sim = 0.0
        else:
            neb = np.zeros(QUERY_EMB_DIM, dtype=np.float64)
            nm = np.zeros(5, dtype=np.float64)
            sim = 0.0
        parts.append(neb)
        parts.append(nm)
        parts.append(np.array([sim], dtype=np.float64))
    out = np.concatenate(parts).astype(np.float64)
    if out.size != FEATURE_DIM:
        out = np.resize(out, FEATURE_DIM)
    return out


def load_model(artifacts_dir: Path) -> tuple[Any, Any] | None:
    """
    Load refinement model and scaler from artifacts_dir.
    Returns (model, scaler_X) or None if not present.
    """
    path = artifacts_dir / "refinement_model.joblib"
    if not path.is_file():
        return None
    try:
        import joblib
        obj = joblib.load(path)
        if isinstance(obj, dict):
            return (obj.get("model"), obj.get("scaler_X"))
        return (obj, None)
    except Exception:
        return None


def predict(
    query_embedding: np.ndarray,
    initial_macros: dict[str, float],
    similar_dishes: list[dict[str, Any]],
    dish_embeddings: dict[str, dict],
    model_and_scaler: tuple[Any, Any],
    macro_delta_stats: dict[str, dict] | None = None,
    clamp_to_bounds: bool = True,
) -> dict[str, float]:
    """
    Predict refined macros using the learned model.
    If clamp_to_bounds and macro_delta_stats provided, clamp each macro to
    initial * (1 + p10) .. initial * (1 + p90).
    """
    model, scaler_X = model_and_scaler
    X = build_feature_vector(
        query_embedding,
        initial_macros,
        similar_dishes,
        dish_embeddings,
    )
    X = X.reshape(1, -1)
    if scaler_X is not None:
        X = scaler_X.transform(X)
    pred = model.predict(X)
    pred = np.asarray(pred).ravel()
    refined = {k: float(pred[i]) for i, k in enumerate(MACRO_KEYS)}
    if clamp_to_bounds and macro_delta_stats and initial_macros:
        for key in MACRO_KEYS:
            base = initial_macros.get(key, 0) or 1e-9
            stats = macro_delta_stats.get(key, {})
            p10 = stats.get("p10", -1.0)
            p90 = stats.get("p90", 1.0)
            low = base * (1 + p10)
            high = base * (1 + p90)
            refined[key] = max(low, min(high, refined[key]))
    return refined
