"""
Configuration for Layer 2 calibration engine.
"""

# Default multipliers when no data is available
DEFAULT_MULTIPLIERS = {
    "calories": 1.0,
    "fat": 1.0,
    "carbs": 1.0,
    "protein": 1.0,
    "sodium": 1.0,
}

# Minimum samples required for reliable multiplier
MIN_SAMPLES_FOR_CONFIDENCE = 5

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.7
MEDIUM_CONFIDENCE_THRESHOLD = 0.4

# Robust statistics parameters
TRIMMED_MEAN_PERCENT = 0.1  # Trim 10% from each tail
MEDIAN_FALLBACK_THRESHOLD = 3  # Use median if fewer than 3 samples

# Fallback hierarchy
FALLBACK_ORDER = [
    "restaurant",
    "cuisine",
    "cooking_method",
    "sauce_level",
    "portion_class",
    "oil_intensity",
    "processing_level",
    "default"
]

# Price bucket thresholds (if available in data)
PRICE_BUCKETS = {
    "cheap": 0.0,
    "mid": 10.0,
    "premium": 20.0,
}
