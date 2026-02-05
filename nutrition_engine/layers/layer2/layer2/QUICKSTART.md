# Layer 2 Quick Start Guide

## Prerequisites

Install required dependencies:

```bash
pip install numpy pandas
```

Or install from requirements:

```bash
pip install -r layer2/requirements.txt
```

## Step 1: Generate Dataset (Part B)

First, ensure you have the restaurant nutrition dataset:

```bash
# Run the notebook to generate the dataset
# Or use the existing dataset at:
# data/processed/restaurant_nutrition_dataset.csv
```

## Step 2: Train the Model

Train the calibration model on your dataset:

```bash
# Quick training (uses first 5000 samples)
python3 layer2/train_model.py

# Or with custom options
python3 layer2/train_model.py \
    --data data/processed/restaurant_nutrition_dataset.csv \
    --output layer2/trained_model.pkl \
    --max-samples 5000
```

This will:
- Load the restaurant nutrition dataset
- Generate simulated Layer 1 baseline estimates
- Train the calibration model
- Save the model to `layer2/trained_model.pkl`

## Step 3: Test Integration

Verify everything works:

```bash
python3 layer2/test_integration.py
```

This tests:
- Calibration without model (fallback mode)
- Feature extraction
- Calibration with trained model (if available)

## Step 4: Monitor Confidence

Analyze model quality:

```bash
python3 layer2/monitor_confidence.py
```

This shows:
- Sample counts per restaurant
- Confidence scores
- High variance cases
- Recommendations

## Step 5: Use in Your Code

```python
from layer2 import calibrate
import pickle

# Load trained model
with open('layer2/trained_model.pkl', 'rb') as f:
    model = pickle.load(f)

from layer2.inference import set_model
set_model(model)

# Calibrate a Layer 1 output
from layer2.schemas import BaselineEstimate

baseline = BaselineEstimate(
    item_name="Big Mac",
    ingredients=["beef", "bun", "cheese"],
    cooking_methods=["fried", "grilled"],
    sauces=["mayo"],
    portion_class="entree",
    macros={
        "calories": 500.0,
        "fat": 25.0,
        "carbs": 45.0,
        "protein": 20.0,
        "sodium": 900.0
    }
)

result = calibrate(
    baseline_estimate=baseline,
    restaurant_metadata={"restaurant": "McDonald's"}
)

print(f"Adjusted calories: {result['adjusted_macros']['calories']:.1f}")
print(f"Confidence: {result['confidence']['calories']:.2f}")
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'pandas'"

Install dependencies:
```bash
pip install numpy pandas
```

### "Dataset not found"

Make sure you've run the notebook to generate the dataset:
- Check `data/processed/restaurant_nutrition_dataset.csv` exists
- Or specify a different path with `--data` flag

### "No valid training data found"

Check that your dataset has:
- `chain` column (restaurant name)
- `item_name` column
- At least one nutrition column (`calories`, `fat`, `carbs`, `protein`, or `sodium`)

### Low confidence scores

- Add more training data for specific restaurants
- Check data quality (no missing values, valid numbers)
- Review high variance cases with `monitor_confidence.py`

## Next Steps

1. **Integrate with Layer 1**: Replace simulated baselines with real Layer 1 outputs
2. **Add more restaurants**: Include more chains in your dataset for better coverage
3. **Tune parameters**: Adjust `config.py` for your use case
4. **Monitor performance**: Regularly run `monitor_confidence.py` to track model quality
