"""
Type definitions and schemas for Layer 2.
"""

from typing import TypedDict, List, Dict, Optional


class BaselineEstimate(TypedDict):
    """Input from Layer 1 - DO NOT MODIFY"""
    item_name: str
    ingredients: List[str]
    cooking_methods: List[str]
    sauces: List[str]
    portion_class: str  # snack | entree | platter
    macros: Dict[str, float]  # calories, fat, carbs, protein, sodium


class RestaurantTruth(TypedDict):
    """Input from Part B dataset"""
    chain: str
    item_name: str
    calories: float
    fat: float
    carbs: float
    protein: float
    sodium: float


class FeatureVector(TypedDict):
    """Extracted features for calibration"""
    restaurant: str
    cuisine: str
    cooking_methods: List[str]
    oil_intensity: str  # low | medium | high
    sauce_level: str  # none | light | medium | heavy
    processing_level: str  # fresh | processed | ultra_processed
    portion_class: str  # snack | entree | platter
    price_bucket: str  # cheap | mid | premium


class CalibrationResult(TypedDict):
    """Output from calibration"""
    adjusted_macros: Dict[str, float]
    confidence: Dict[str, float]
    applied_adjustments: Dict[str, Dict[str, float]]  # macro -> adjustment_type -> multiplier
