"""Straight-through pipeline: Layer 1 → Layer 2 → Layer 3. No branching."""

from app.schemas import (
    NutritionRequest,
    NutritionResponse,
    Layer1Output,
    Layer2Output,
    Layer3Output,
)
from layers import layer1, layer2, layer3

# Required keys for each handoff (L1 out = L2 in; L2 out = L3 in)
_L1_KEYS = frozenset(Layer1Output.__annotations__)
_L2_KEYS = frozenset(Layer2Output.__annotations__)
_L3_KEYS = frozenset(Layer3Output.__annotations__)


def _check_layer1_output(data: dict) -> Layer1Output:
    """Ensure L1 output has exact shape expected by Layer 2 (baseline_estimate)."""
    missing = _L1_KEYS - set(data)
    if missing:
        raise ValueError(f"Layer 1 output missing keys expected by Layer 2: {missing}")
    return data  # type: ignore[return-value]


def _check_layer2_output(data: dict) -> Layer2Output:
    """Ensure L2 output has exact shape expected by Layer 3 (l2_output)."""
    missing = _L2_KEYS - set(data)
    if missing:
        raise ValueError(f"Layer 2 output missing keys expected by Layer 3: {missing}")
    return data  # type: ignore[return-value]


def _check_layer3_output(data: dict) -> Layer3Output:
    """Ensure L3 output has keys the engine consumes (final_macros, etc.)."""
    missing = _L3_KEYS - set(data)
    if missing:
        raise ValueError(f"Layer 3 output missing required keys: {missing}")
    return data  # type: ignore[return-value]


def estimate_nutrition(req: NutritionRequest) -> NutritionResponse:
    # 1️⃣ Layer 1 — baseline estimate
    l1_out = layer1.estimate(
        item_name=req["item_name"],
        description=req["description"],
        modifiers=req.get("modifiers"),
    )
    l1_out = _check_layer1_output(l1_out)

    # 2️⃣ Layer 2 — restaurant calibration (input = L1 output shape)
    l2_out = layer2.calibrate(
        baseline_estimate=l1_out,
        restaurant_metadata={
            "restaurant": req.get("restaurant"),
            "price": req.get("price"),
        },
    )
    l2_out = _check_layer2_output(l2_out)

    # 3️⃣ Layer 3 — similarity refinement (input = L2 output shape)
    l3_out = layer3.apply_layer3(l2_out)
    l3_out = _check_layer3_output(l3_out)

    # Confidence aggregation (fixed v1 rule)
    confidence = (
        0.5 * l1_out.get("confidence", 1.0)
        + 0.3 * l2_out.get("layer2_confidence", 1.0)
        + 0.2 * l3_out.get("layer3_confidence", 1.0)
    )

    return {
        "macros": l3_out["final_macros"],
        "confidence": confidence,
        "debug": {
            "layer2_adjustments": l2_out.get("applied_adjustments"),
            "layer3_refinements": l3_out.get("refinements_applied"),
        },
    }
