"""
Load Layer 3 artifacts (read-only). Artifacts are built by layer3_artifact_build.ipynb.
"""
from pathlib import Path
from typing import Any

import json
import pickle


DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"

COOKING_METHODS_ORDER = [
    "raw", "steamed", "boiled", "baked", "grilled", "fried", "sauteed", "roasted", "other"
]
PORTION_CLASSES = ["small", "medium", "large"]


def load_ingredient_embeddings(artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR) -> dict[str, Any]:
    with open(artifacts_dir / "ingredient_embeddings.pkl", "rb") as f:
        return pickle.load(f)


def load_dish_embeddings(artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR) -> dict[str, Any]:
    with open(artifacts_dir / "dish_embeddings.pkl", "rb") as f:
        return pickle.load(f)


def load_neighbor_index(artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR) -> dict[str, list]:
    with open(artifacts_dir / "neighbor_index.pkl", "rb") as f:
        return pickle.load(f)


def load_macro_delta_stats(artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR) -> dict[str, dict]:
    with open(artifacts_dir / "macro_delta_stats.json") as f:
        return json.load(f)


def load_confidence_params(artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR) -> dict[str, Any]:
    with open(artifacts_dir / "confidence_params.json") as f:
        return json.load(f)


def load_all(artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR) -> dict[str, Any]:
    """Load all artifacts. Keys: ingredient_embeddings, dish_embeddings, neighbor_index, macro_delta_stats, confidence_params."""
    return {
        "ingredient_embeddings": load_ingredient_embeddings(artifacts_dir),
        "dish_embeddings": load_dish_embeddings(artifacts_dir),
        "neighbor_index": load_neighbor_index(artifacts_dir),
        "macro_delta_stats": load_macro_delta_stats(artifacts_dir),
        "confidence_params": load_confidence_params(artifacts_dir),
    }
