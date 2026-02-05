"""
Confidence scoring for calibration adjustments.
"""

try:
    import numpy as np
except ImportError:
    # Fallback if numpy not available
    class np:
        @staticmethod
        def var(x):
            if len(x) == 0:
                return 0
            mean = sum(x) / len(x)
            return sum((xi - mean) ** 2 for xi in x) / len(x)
        @staticmethod
        def std(x):
            return np.var(x) ** 0.5
        @staticmethod
        def mean(x):
            return sum(x) / len(x) if len(x) > 0 else 0
        @staticmethod
        def clip(x, min_val, max_val):
            return max(min_val, min(max_val, x))

from typing import Dict
from .schemas import FeatureVector
from .config import (
    MIN_SAMPLES_FOR_CONFIDENCE,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
)
from .calibration_model import CalibrationModel


def confidence_score(
    model: CalibrationModel,
    features: FeatureVector,
    macro: str
) -> float:
    """
    Compute confidence score (0.0 - 1.0) for a given macro adjustment.
    
    Based on:
    - Number of real samples backing the multiplier
    - Variance in observed ratios
    - Ontology match strength
    
    Args:
        model: Trained CalibrationModel
        features: FeatureVector for the item
        macro: Macro name (calories, fat, carbs, protein, sodium)
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Get sample count
    sample_count = model.get_sample_count(features, macro)
    
    # Base confidence from sample count
    if sample_count == 0:
        return 0.1  # Very low confidence if no data
    
    if sample_count < MIN_SAMPLES_FOR_CONFIDENCE:
        # Low confidence for few samples
        sample_confidence = 0.3 + (sample_count / MIN_SAMPLES_FOR_CONFIDENCE) * 0.3
    else:
        # Higher confidence with more samples (capped)
        sample_confidence = min(0.9, 0.6 + (sample_count / 50) * 0.3)
    
    # Get variance-based confidence
    variance_confidence = _compute_variance_confidence(model, features, macro)
    
    # Ontology match strength
    ontology_confidence = _compute_ontology_confidence(features)
    
    # Weighted combination
    confidence = (
        0.5 * sample_confidence +
        0.3 * variance_confidence +
        0.2 * ontology_confidence
    )
    
    return float(np.clip(confidence, 0.0, 1.0))


def _compute_variance_confidence(
    model: CalibrationModel,
    features: FeatureVector,
    macro: str
) -> float:
    """Compute confidence based on variance in observed ratios."""
    # Try to get ratios for this feature combination
    restaurant = features["restaurant"]
    ratios = []
    
    if restaurant in model.multipliers["restaurant"]:
        ratios = model.multipliers["restaurant"][restaurant].get(macro, [])
    
    if not ratios:
        # Fall back to cuisine
        cuisine = features["cuisine"]
        if cuisine in model.multipliers["cuisine"]:
            ratios = model.multipliers["cuisine"][cuisine].get(macro, [])
    
    if len(ratios) < 2:
        return 0.5  # Neutral if not enough data
    
    # Lower variance = higher confidence
    variance = np.var(ratios)
    std = np.std(ratios)
    mean = np.mean(ratios)
    
    if mean == 0:
        return 0.5
    
    # Coefficient of variation
    cv = std / mean if mean > 0 else 1.0
    
    # Lower CV = higher confidence
    # CV < 0.1: high confidence (0.9)
    # CV < 0.3: medium confidence (0.7)
    # CV < 0.5: low-medium confidence (0.5)
    # CV >= 0.5: low confidence (0.3)
    if cv < 0.1:
        return 0.9
    elif cv < 0.3:
        return 0.7
    elif cv < 0.5:
        return 0.5
    else:
        return 0.3


def _compute_ontology_confidence(features: FeatureVector) -> float:
    """
    Compute confidence based on ontology match strength.
    Higher confidence if features are well-defined and match ontology.
    """
    confidence = 1.0
    
    # Penalize unknown restaurant
    if features["restaurant"] == "unknown":
        confidence *= 0.7
    
    # Penalize default cuisine
    if features["cuisine"] == "american" and "unknown" not in features["restaurant"].lower():
        # American is default, might be less specific
        confidence *= 0.9
    
    # Penalize if cooking methods are default
    if features["cooking_methods"] == ["fried"]:
        confidence *= 0.9
    
    # Boost if we have specific features
    if features["sauce_level"] != "none":
        confidence *= 1.05  # Slight boost for specificity
    
    if features["processing_level"] != "processed":
        confidence *= 1.05  # Slight boost for specificity
    
    return min(1.0, confidence)
