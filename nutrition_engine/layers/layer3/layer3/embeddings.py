"""
Embed a dish from ingredients + cooking methods + sauce + portion (same formula as notebook).
Uses ingredient_embeddings.pkl; OOV ingredients get mean embedding.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from .loader import COOKING_METHODS_ORDER, PORTION_CLASSES

METHOD_TO_IDX = {m: i for i, m in enumerate(COOKING_METHODS_ORDER)}
PORTION_TO_IDX = {p: i for i, p in enumerate(PORTION_CLASSES)}


def encode_cooking_methods(methods: list[str] | str) -> np.ndarray:
    vec = np.zeros(len(COOKING_METHODS_ORDER), dtype=np.float32)
    for m in (methods if isinstance(methods, (list, tuple)) else [methods]):
        m = m.strip().lower() if isinstance(m, str) else "other"
        idx = METHOD_TO_IDX.get(m, METHOD_TO_IDX["other"])
        vec[idx] = 1.0
    return vec


def encode_portion(portion_class: str | None) -> np.ndarray:
    vec = np.zeros(len(PORTION_CLASSES), dtype=np.float32)
    pc = (portion_class or "medium").strip().lower()
    idx = PORTION_TO_IDX.get(pc, PORTION_TO_IDX["medium"])
    vec[idx] = 1.0
    return vec


def embed_dish(
    ingredients: list[str],
    cooking_methods: list[str],
    sauces: float,
    portion_class: str,
    ingredient_embeddings: dict[str, np.ndarray],
    mean_embedding: np.ndarray | None = None,
) -> np.ndarray:
    """
    Build dish embedding = mean(ingredient_embeddings) + method_vec + sauce_scalar + portion_vec.
    Ingredients not in embedding dict use mean_embedding; if None, compute from ingredient_embeddings.
    """
    if mean_embedding is None:
        mean_embedding = np.mean(list(ingredient_embeddings.values()), axis=0)
    ings = [str(x).strip().lower() for x in ingredients]
    mean_ing = np.mean(
        [ingredient_embeddings.get(ing, mean_embedding) for ing in ings],
        axis=0,
    )
    method_vec = encode_cooking_methods(cooking_methods)
    sauce_scalar = np.array([float(sauces)], dtype=np.float32)
    portion_vec = encode_portion(portion_class)
    return np.concatenate([mean_ing, method_vec, sauce_scalar, portion_vec])
