# Layer 2: Restaurant Calibration Engine

## Overview

Layer 2 learns restaurant-specific empirical adjustments to Layer 1 baseline nutrition estimates. It calibrates Layer 1 outputs using real restaurant nutrition disclosures to account for systematic deviations.

## How It Works

### Core Concept

Layer 2 learns **multipliers** that adjust Layer 1 baseline estimates:

```
adjusted_macro = baseline_macro × multiplier
```

Multipliers are learned at multiple levels:
- **Restaurant level**: Chain-specific adjustments
- **Cuisine level**: Cuisine-type adjustments (fallback)
- **Cooking method level**: Method-specific adjustments
- **Sauce level**: Sauce intensity adjustments
- **Portion class**: Size-based adjustments
- **Oil intensity**: Oil usage adjustments
- **Processing level**: Processing degree adjustments

### Fallback Hierarchy

When data is missing, Layer 2 uses a fallback hierarchy:
1. Restaurant-specific multiplier (most specific)
2. Cuisine-level multiplier
3. Cooking method multiplier
4. Default multiplier (1.0)

### Robust Statistics

Layer 2 uses robust statistical methods:
- **Trimmed mean**: Removes outliers (10% from each tail)
- **Median fallback**: Uses median for small samples (< 3)
- **Outlier removal**: Filters ratios beyond 3 standard deviations

### Confidence Scoring

Confidence scores (0.0 - 1.0) are computed based on:
- **Sample count**: More samples = higher confidence
- **Variance**: Lower variance = higher confidence
- **Ontology match**: Better feature match = higher confidence

## Integration Contract with Layer 1

### Input from Layer 1

Layer 2 accepts the following structure **without modification**:

```python
BaselineEstimate = {
    "item_name": str,
    "ingredients": list[str],
    "cooking_methods": list[str],
    "sauces": list[str],
    "portion_class": str,  # snack | entree | platter
    "macros": {
        "calories": float,
        "fat": float,
        "carbs": float,
        "protein": float,
        "sodium": float
    }
}
```

### Output to Consumer

Layer 2 returns:

```python
{
    "adjusted_macros": {
        "calories": float,
        "fat": float,
        "carbs": float,
        "protein": float,
        "sodium": float
    },
    "confidence": {
        "calories": float,  # 0.0 - 1.0
        "fat": float,
        "carbs": float,
        "protein": float,
        "sodium": float
    },
    "applied_adjustments": {
        "calories": {
            "multiplier": float,
            "adjustment_type": str,  # restaurant | cuisine | default
            "baseline": float,
            "adjusted": float
        },
        # ... same for other macros
    }
}
```

## Usage

### Training

```python
from layer2 import CalibrationModel
from layer2.schemas import BaselineEstimate, RestaurantTruth

# Initialize model
model = CalibrationModel()

# Prepare training data
baseline_estimates = [...]  # From Layer 1
restaurant_truths = [...]    # From Part B dataset
restaurant_metadata = [{"restaurant": "McDonald's"}, ...]

# Train
model.train(baseline_estimates, restaurant_truths, restaurant_metadata)

# Set as global model
from layer2.inference import set_model
set_model(model)
```

### Inference

```python
from layer2 import calibrate
from layer2.schemas import BaselineEstimate

# Get baseline from Layer 1
baseline = BaselineEstimate(
    item_name="Big Mac",
    ingredients=["beef", "bun", "cheese", "lettuce"],
    cooking_methods=["fried", "grilled"],
    sauces=["mayo", "special sauce"],
    portion_class="entree",
    macros={
        "calories": 500.0,
        "fat": 25.0,
        "carbs": 45.0,
        "protein": 20.0,
        "sodium": 900.0
    }
)

# Calibrate
result = calibrate(
    baseline_estimate=baseline,
    restaurant_metadata={"restaurant": "McDonald's"}
)

print(result["adjusted_macros"])
print(result["confidence"])
```

## Adding a New Restaurant

### 1. Add Restaurant Data

Add the restaurant's nutrition data to the Part B dataset with:
- `chain`: Restaurant name
- `item_name`: Menu item name
- Nutrition values: `calories`, `fat`, `carbs`, `protein`, `sodium`

### 2. Update Cuisine Mapping (Optional)

If the restaurant represents a new cuisine type, add it to `layer2/ontology.py`:

```python
CUISINE_MAPPING = {
    # ... existing mappings
    "new_restaurant": "new_cuisine",
}
```

### 3. Retrain Model

Retrain the model with the new data:

```python
model.train(baseline_estimates, restaurant_truths, restaurant_metadata)
```

The model will automatically learn multipliers for the new restaurant.

## Failure Modes and Fallbacks

### No Model Available

**Symptom**: Model not trained or not set.

**Behavior**: Returns baseline estimates with confidence = 0.1

**Solution**: Train and set the model before inference.

### Missing Restaurant Data

**Symptom**: No training data for a specific restaurant.

**Behavior**: Falls back to cuisine-level multipliers, then cooking method, then default (1.0)

**Solution**: Add restaurant data to training set, or rely on cuisine-level adjustments.

### Missing Cuisine Data

**Symptom**: No training data for a cuisine type.

**Behavior**: Falls back to cooking method multipliers, then default (1.0)

**Solution**: Add data from restaurants of that cuisine type.

### Zero or Negative Baseline Values

**Symptom**: Layer 1 returns 0 or negative values.

**Behavior**: Skips calibration for that macro, returns baseline value

**Solution**: Ensure Layer 1 outputs valid positive values.

### Low Confidence Scores

**Symptom**: Confidence < 0.4 for adjustments.

**Causes**:
- Few training samples (< 5)
- High variance in observed ratios
- Poor ontology match

**Solution**: 
- Add more training data
- Check data quality
- Verify feature extraction

## Architecture

```
layer2/
├── __init__.py           # Package exports
├── config.py             # Configuration constants
├── schemas.py            # Type definitions
├── ontology.py           # Fixed ontology mappings
├── feature_extraction.py # Deterministic feature extraction
├── calibration_model.py  # Multiplier learning
├── confidence.py         # Confidence scoring
├── inference.py          # Public API
└── README.md             # This file
```

## Constraints

✅ **Allowed**:
- Rule-based feature extraction
- Statistical learning from data
- Deterministic behavior
- Robust statistics

❌ **Not Allowed**:
- LLM calls at training or inference time
- Hardcoded restaurant-specific logic
- Assumptions about Layer 1 internals
- UI or API code

## Testing

Layer 2 can be tested with dummy Layer 1 outputs:

```python
# Dummy baseline
baseline = BaselineEstimate(
    item_name="Test Item",
    ingredients=["test"],
    cooking_methods=["fried"],
    sauces=[],
    portion_class="entree",
    macros={"calories": 100.0, "fat": 10.0, "carbs": 20.0, "protein": 5.0, "sodium": 200.0}
)

# Test calibration
result = calibrate(baseline, {"restaurant": "Test Restaurant"})
assert "adjusted_macros" in result
assert "confidence" in result
```

## Extensibility

Layer 2 is designed to be extended:

1. **New adjustment levels**: Add to `FALLBACK_ORDER` in `config.py`
2. **New features**: Extend `FeatureVector` in `schemas.py`
3. **New statistics**: Modify `_compute_robust_multiplier` in `calibration_model.py`
4. **New confidence factors**: Extend `confidence_score` in `confidence.py`

All extensions maintain the deterministic, rule-based approach.
