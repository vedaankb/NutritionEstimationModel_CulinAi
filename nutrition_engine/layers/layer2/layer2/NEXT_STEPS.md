# Next Steps for Layer 2 Integration

## ✅ Completed

1. **Package Structure**: All required modules created
2. **Core Functionality**: Calibration model, feature extraction, confidence scoring
3. **Training Script**: `train_model.py` ready to use
4. **Test Scripts**: Integration tests and confidence monitoring

## 🚀 Immediate Next Steps

### 1. Install Dependencies

```bash
pip install numpy pandas
```

### 2. Train the Model

```bash
# Option A: Use the setup script (recommended)
python3 layer2/setup_and_train.py

# Option B: Use the training script directly
python3 layer2/train_model.py --max-samples 5000

# Option C: Use the shell script
./layer2/run_training.sh
```

### 3. Verify Training

```bash
# Check model was created
ls -lh layer2/trained_model.pkl

# Run integration tests
python3 layer2/test_integration.py

# Monitor confidence
python3 layer2/monitor_confidence.py
```

## 🔌 Integration with Layer 1

### Step 1: Get Layer 1 Output

When Layer 1 is ready, it will provide `BaselineEstimate` objects. For now, you can simulate:

```python
from layer2.schemas import BaselineEstimate

baseline = BaselineEstimate(
    item_name="Your Item",
    ingredients=["ingredient1", "ingredient2"],
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
```

### Step 2: Calibrate

```python
from layer2 import calibrate
import pickle

# Load trained model
with open('layer2/trained_model.pkl', 'rb') as f:
    model = pickle.load(f)

from layer2.inference import set_model
set_model(model)

# Calibrate
result = calibrate(
    baseline_estimate=baseline,
    restaurant_metadata={"restaurant": "McDonald's"}
)

# Use results
adjusted_calories = result['adjusted_macros']['calories']
confidence = result['confidence']['calories']
```

### Step 3: Handle Low Confidence

```python
# Check confidence before using
if result['confidence']['calories'] < 0.4:
    print("⚠️  Low confidence - consider manual review")
    # Fall back to baseline or flag for review
```

## 📊 Monitoring and Maintenance

### Regular Tasks

1. **Monitor Confidence** (weekly):
   ```bash
   python3 layer2/monitor_confidence.py
   ```

2. **Add New Restaurants**:
   - Add restaurant data to Part B dataset
   - Retrain model: `python3 layer2/train_model.py`

3. **Review High Variance Cases**:
   - Check `monitor_confidence.py` output
   - Investigate restaurants with variance > 0.1

### Model Updates

When you get more data:

```bash
# Retrain with all data (no max-samples limit)
python3 layer2/train_model.py --max-samples None

# Or with specific dataset
python3 layer2/train_model.py \
    --data your_new_dataset.csv \
    --output layer2/trained_model_v2.pkl
```

## 🧪 Testing Strategy

### Unit Tests

Test individual components:

```python
from layer2.feature_extraction import extract_features
from layer2.schemas import BaselineEstimate

# Test feature extraction
baseline = BaselineEstimate(...)
features = extract_features(baseline, {"restaurant": "McDonald's"})
assert features['cuisine'] == 'american'
```

### Integration Tests

Test full pipeline:

```python
# Test calibration end-to-end
result = calibrate(baseline, {"restaurant": "McDonald's"})
assert 'adjusted_macros' in result
assert 'confidence' in result
```

### Validation Tests

Test on held-out data:

```python
# Split your dataset
train_data = df.head(80)
test_data = df.tail(20)

# Train on train_data
# Validate on test_data
# Compare adjusted vs actual
```

## 🔧 Customization

### Adjust Configuration

Edit `layer2/config.py`:

```python
# Change minimum samples for confidence
MIN_SAMPLES_FOR_CONFIDENCE = 10  # Default: 5

# Change trimmed mean percentage
TRIMMED_MEAN_PERCENT = 0.15  # Default: 0.1
```

### Add New Cuisines

Edit `layer2/ontology.py`:

```python
CUISINE_MAPPING = {
    # ... existing mappings
    "new_restaurant": "new_cuisine",
}
```

### Extend Feature Extraction

Edit `layer2/feature_extraction.py`:

```python
def _determine_new_feature(...):
    # Add your logic
    pass
```

## 📈 Performance Optimization

### Speed Up Training

```python
# Use fewer samples for quick iteration
python3 layer2/train_model.py --max-samples 1000

# Use all samples for production
python3 layer2/train_model.py --max-samples None
```

### Cache Model

```python
# Load model once, reuse
model = pickle.load(open('layer2/trained_model.pkl', 'rb'))
set_model(model)

# Now calibrate many items without reloading
for item in items:
    result = calibrate(item, metadata)
```

## 🐛 Debugging

### Low Confidence Issues

1. Check sample counts:
   ```bash
   python3 layer2/monitor_confidence.py
   ```

2. Add more training data for low-confidence restaurants

3. Check data quality (no missing values, valid numbers)

### Incorrect Adjustments

1. Check applied adjustments:
   ```python
   print(result['applied_adjustments'])
   ```

2. Verify restaurant name matches training data

3. Check feature extraction:
   ```python
   from layer2.feature_extraction import extract_features
   features = extract_features(baseline, metadata)
   print(features)
   ```

## 📚 Documentation

- **README.md**: Complete documentation
- **QUICKSTART.md**: Quick start guide
- **example_usage.py**: Usage examples
- **schemas.py**: Type definitions

## 🎯 Success Criteria

Layer 2 is working correctly when:

- ✅ Model trains without errors
- ✅ Calibration produces adjusted values different from baseline
- ✅ Confidence scores are reasonable (0.3 - 1.0)
- ✅ Integration tests pass
- ✅ Can handle new restaurants (falls back gracefully)

## 🚨 Common Issues

### "No module named 'layer2'"

Make sure you're in the project root:
```bash
cd /path/to/Layer2_CulinAi
python3 layer2/train_model.py
```

### "Model not found"

Train the model first:
```bash
python3 layer2/train_model.py
```

### "Dataset not found"

Generate the dataset:
- Run the notebook: `build_nutrition_dataset.ipynb`
- Or check: `data/processed/restaurant_nutrition_dataset.csv`

### All multipliers are 1.0

This means no adjustments are being applied. Check:
- Model was trained successfully
- Restaurant names match between training and inference
- Training data had valid nutrition values
