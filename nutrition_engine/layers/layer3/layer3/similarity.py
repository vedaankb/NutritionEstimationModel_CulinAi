"""
Find similar dishes by cosine similarity. Uses dish_embeddings; for known dish_id can use neighbor_index.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def top_k_similar(
    query_embedding: np.ndarray,
    dish_embeddings: dict[str, dict],
    k: int = 7,
) -> list[dict[str, Any]]:
    """
    Return top-k dish_ids by cosine similarity to query_embedding.
    Each item: {"dish_id": str, "similarity": float, "macros": {...}}
    """
    dish_ids = list(dish_embeddings.keys())
    sims = []
    for did in dish_ids:
        sim = cosine_sim(query_embedding, dish_embeddings[did]["embedding"])
        sims.append((did, sim, dish_embeddings[did]["macros"]))
    sims.sort(key=lambda x: -x[1])
    return [
        {"dish_id": did, "similarity": sim, "macros": macros}
        for did, sim, macros in sims[:k]
    ]


def get_neighbors_for_embedding(
    query_embedding: np.ndarray,
    dish_embeddings: dict[str, dict],
    k: int = 7,
) -> list[dict[str, Any]]:
    """
    Same as top_k_similar but also computes macro_deltas relative to a reference.
    Caller can pass reference_macros to get deltas; here we just return top-k with similarity and macros.
    For refinement, caller will use these neighbors' macros and similarity to compute weighted deltas.
    """
    return top_k_similar(query_embedding, dish_embeddings, k)
