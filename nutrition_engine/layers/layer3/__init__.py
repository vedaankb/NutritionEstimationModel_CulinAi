"""Layer 3: similarity refinement. Real implementation from CulinAIAPP-Layer3."""

import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_loaded = False
_artifacts: Dict[str, Any] | None = None


def load_embeddings(artifacts_path: str) -> None:
    """Load Layer 3 artifacts (embeddings, neighbor index, etc.). Call once at startup."""
    global _loaded, _artifacts
    path = Path(artifacts_path)
    try:
        from layers.layer3.layer3 import loader
        _artifacts = loader.load_all(path)
        _loaded = True
        logger.info("Layer 3: loaded embeddings and artifacts from %s", path)
    except FileNotFoundError as e:
        logger.warning("Layer 3: artifacts not found at %s (%s); refinement will pass through", path, e)
        _artifacts = None
        _loaded = True
    except Exception as e:
        logger.warning("Layer 3: failed to load artifacts from %s: %s; refinement will pass through", path, e)
        _artifacts = None
        _loaded = True


def apply_layer3(l2_output: Dict[str, Any]) -> Dict[str, Any]:
    """Refine calibrated estimate. Returns final_macros, layer3_confidence, refinements_applied."""
    macros = l2_output.get("macros", {})
    if _artifacts is None:
        return {
            "final_macros": dict(macros),
            "layer3_confidence": 1.0,
            "refinements_applied": {},
        }
    try:
        from layers.layer3.layer3 import refine

        initial_macros = {
            "calories": macros.get("calories", 0.0),
            "fat": macros.get("fat", 0.0),
            "carbs": macros.get("carbs", 0.0),
            "protein": macros.get("protein", 0.0),
            "sodium": macros.get("sodium", 0.0),
        }
        result = refine(
            ingredients=[],
            cooking_methods=["baked"],
            sauces=0.2,
            portion_class="medium",
            initial_macros=initial_macros,
            artifacts=_artifacts,
            top_k=7,
        )
        return {
            "final_macros": result.refined_macros,
            "layer3_confidence": result.confidence,
            "refinements_applied": {"similar_dish_ids": result.similar_dish_ids[:5]},
        }
    except Exception as e:
        logger.warning("Layer 3 refinement failed: %s; passing through L2 macros", e)
        return {
            "final_macros": dict(macros),
            "layer3_confidence": 1.0,
            "refinements_applied": {},
        }
