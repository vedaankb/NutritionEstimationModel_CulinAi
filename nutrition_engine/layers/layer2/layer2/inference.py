"""
Public inference API - the ONLY entry point for Layer 2.
"""

from typing import Dict, Optional
from .schemas import BaselineEstimate, CalibrationResult, FeatureVector
from .feature_extraction import extract_features
from .calibration_model import CalibrationModel
from .confidence import confidence_score
from .config import DEFAULT_MULTIPLIERS


# Global model instance (should be trained before use)
_model: Optional[CalibrationModel] = None


def set_model(model: CalibrationModel):
    """Set the global calibration model."""
    global _model
    _model = model


def get_model() -> Optional[CalibrationModel]:
    """Get the global calibration model."""
    return _model


def calibrate(
    baseline_estimate: BaselineEstimate,
    restaurant_metadata: Dict,
    model: Optional[CalibrationModel] = None
) -> CalibrationResult:
    """
    Main calibration function - the ONLY public entry point.
    
    Args:
        baseline_estimate: Input from Layer 1 (DO NOT MODIFY)
        restaurant_metadata: Dict with 'restaurant' (chain name) and optionally 'price'
        model: Optional CalibrationModel (uses global if not provided)
    
    Returns:
        CalibrationResult with adjusted macros, confidence scores, and applied adjustments
    """
    # Use provided model or global model
    if model is None:
        model = _model
    
    if model is None:
        # No model available - return baseline with low confidence
        return _fallback_calibration(baseline_estimate)
    
    # Extract features
    features = extract_features(baseline_estimate, restaurant_metadata)
    
    # Get multipliers
    multipliers_dict = model.get_multipliers(features)
    
    # Apply multipliers to each macro
    adjusted_macros = {}
    confidence_scores = {}
    applied_adjustments = {}
    
    macros = ["calories", "fat", "carbs", "protein", "sodium"]
    
    for macro in macros:
        baseline_val = baseline_estimate["macros"].get(macro, 0.0)
        
        # Get the best multiplier (prefer restaurant, then cuisine, then default)
        multiplier = DEFAULT_MULTIPLIERS[macro]
        adjustment_type = "default"
        
        if macro in multipliers_dict:
            macro_multipliers = multipliers_dict[macro]
            # Prefer restaurant > cuisine > cooking_method > default
            for level in ["restaurant", "cuisine", "cooking_method", "sauce_level", 
                         "portion_class", "oil_intensity", "processing_level", "default"]:
                if level in macro_multipliers:
                    multiplier = macro_multipliers[level]
                    adjustment_type = level
                    break
        
        # Apply multiplier
        adjusted_val = baseline_val * multiplier
        adjusted_macros[macro] = adjusted_val
        
        # Compute confidence
        conf = confidence_score(model, features, macro)
        confidence_scores[macro] = conf
        
        # Store applied adjustment
        applied_adjustments[macro] = {
            "multiplier": multiplier,
            "adjustment_type": adjustment_type,
            "baseline": baseline_val,
            "adjusted": adjusted_val,
        }
    
    return CalibrationResult(
        adjusted_macros=adjusted_macros,
        confidence=confidence_scores,
        applied_adjustments=applied_adjustments,
    )


def _fallback_calibration(baseline_estimate: BaselineEstimate) -> CalibrationResult:
    """Fallback when no model is available."""
    macros = ["calories", "fat", "carbs", "protein", "sodium"]
    
    adjusted_macros = {
        macro: baseline_estimate["macros"].get(macro, 0.0)
        for macro in macros
    }
    
    confidence_scores = {
        macro: 0.1  # Very low confidence
        for macro in macros
    }
    
    applied_adjustments = {
        macro: {
            "multiplier": 1.0,
            "adjustment_type": "no_model",
            "baseline": baseline_estimate["macros"].get(macro, 0.0),
            "adjusted": baseline_estimate["macros"].get(macro, 0.0),
        }
        for macro in macros
    }
    
    return CalibrationResult(
        adjusted_macros=adjusted_macros,
        confidence=confidence_scores,
        applied_adjustments=applied_adjustments,
    )
