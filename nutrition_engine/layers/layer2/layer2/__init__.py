"""
Layer 2: Restaurant Calibration Engine

This package learns restaurant-specific empirical adjustments to Layer 1 baseline estimates.
"""

from .inference import calibrate, set_model, get_model
from .calibration_model import CalibrationModel
from .feature_extraction import extract_features
from .confidence import confidence_score

__all__ = [
    'calibrate',
    'set_model',
    'get_model',
    'CalibrationModel',
    'extract_features',
    'confidence_score',
]

__version__ = '1.0.0'
