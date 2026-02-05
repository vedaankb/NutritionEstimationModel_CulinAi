"""Layer 2: restaurant calibration. Real implementation from CulinAIAPP-Layer2."""

import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_loaded = False


def _build_baseline_estimate(baseline_estimate: Dict[str, Any]) -> Dict[str, Any]:
    """Build Layer 2 BaselineEstimate from engine handoff (macros + optional confidence)."""
    macros = baseline_estimate.get("macros", {})
    # Layer 2 expects calories, fat, carbs, protein, sodium
    full_macros = {
        "calories": macros.get("calories", 0.0),
        "fat": macros.get("fat", 0.0),
        "carbs": macros.get("carbs", 0.0),
        "protein": macros.get("protein", 0.0),
        "sodium": macros.get("sodium", 0.0),
    }
    return {
        "item_name": "",
        "ingredients": [],
        "cooking_methods": ["fried"],
        "sauces": [],
        "portion_class": "entree",
        "macros": full_macros,
    }


def load_calibration_tables(artifacts_path: str) -> None:
    """Load Layer 2 model from artifacts (trained_model.pkl). Call once at startup."""
    global _loaded
    path = Path(artifacts_path)
    model_file = path / "trained_model.pkl"
    if not model_file.exists():
        logger.warning("Layer 2: no trained_model.pkl at %s; calibration will use fallback", path)
        _loaded = True
        return
    try:
        import pickle
        import sys
        # So pickle can resolve "layer2.xxx" to layers.layer2.layer2
        _layer2_dir = Path(__file__).resolve().parent
        if str(_layer2_dir) not in sys.path:
            sys.path.insert(0, str(_layer2_dir))
        from layers.layer2.layer2.inference import set_model
        with open(model_file, "rb") as f:
            model = pickle.load(f)
        set_model(model)
        _loaded = True
        logger.info("Layer 2: loaded calibration model from %s", model_file)
    except Exception as e:
        logger.warning("Layer 2: failed to load model from %s: %s; using fallback", model_file, e)
        _loaded = True


def calibrate(
    baseline_estimate: Dict[str, Any],
    restaurant_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Calibrate baseline using restaurant/price. Returns macros, layer2_confidence, applied_adjustments."""
    from layers.layer2.layer2.inference import calibrate as _calibrate

    base = _build_baseline_estimate(baseline_estimate)
    result = _calibrate(baseline_estimate=base, restaurant_metadata=restaurant_metadata)

    adjusted = result.get("adjusted_macros", result.get("macros", {}))
    conf_dict = result.get("confidence", {})
    if isinstance(conf_dict, dict) and conf_dict:
        layer2_confidence = sum(conf_dict.values()) / len(conf_dict)
    else:
        layer2_confidence = 1.0

    return {
        "macros": adjusted,
        "layer2_confidence": float(layer2_confidence),
        "applied_adjustments": result.get("applied_adjustments", {}),
    }
