"""Unified request/response schema and layer handoff contracts."""

from typing import TypedDict, Optional, List, Dict, Any


class NutritionRequest(TypedDict):
    item_name: str
    description: str
    restaurant: Optional[str]
    price: Optional[float]
    modifiers: Optional[List[str]]


class NutritionResponse(TypedDict):
    macros: Dict[str, float]
    confidence: float
    debug: Dict


# --- Layer handoff contracts (L1 out = L2 in; L2 out = L3 in) ---

class Macros(TypedDict, total=False):
    """Macro keys; all floats. total=False allows subsets during pipeline."""
    calories: float
    protein: float
    carbs: float
    fat: float


class Layer1Output(TypedDict):
    """What Layer 1 returns. This is exactly what Layer 2 receives as baseline_estimate."""
    macros: Dict[str, float]
    confidence: float


# Layer 2 input = Layer1Output (baseline_estimate)


class Layer2Output(TypedDict):
    """What Layer 2 returns. This is exactly what Layer 3 receives as l2_output."""
    macros: Dict[str, float]
    layer2_confidence: float
    applied_adjustments: Dict[str, Any]


# Layer 3 input = Layer2Output (l2_output)


class Layer3Output(TypedDict):
    """What Layer 3 returns."""
    final_macros: Dict[str, float]
    layer3_confidence: float
    refinements_applied: Dict[str, Any]
