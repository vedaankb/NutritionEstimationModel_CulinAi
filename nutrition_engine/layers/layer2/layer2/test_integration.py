"""
Integration test script for Layer 2.

Tests the calibration engine with dummy Layer 1 outputs.
"""

import sys
from pathlib import Path
import pickle

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from layer2 import calibrate, CalibrationModel, set_model
from .schemas import BaselineEstimate


def test_without_model():
    """Test that calibration works even without a trained model."""
    print("=" * 60)
    print("Test 1: Calibration without trained model")
    print("=" * 60)
    
    baseline = BaselineEstimate(
        item_name="Test Burger",
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
        restaurant_metadata={"restaurant": "Test Restaurant"}
    )
    
    print(f"✅ Calibration completed (fallback mode)")
    print(f"   Adjusted calories: {result['adjusted_macros']['calories']:.1f}")
    print(f"   Confidence: {result['confidence']['calories']:.2f}")
    assert result['adjusted_macros']['calories'] == 500.0  # No adjustment without model
    assert result['confidence']['calories'] < 0.2  # Low confidence
    print("✅ Test passed!\n")


def test_with_model():
    """Test calibration with a trained model."""
    print("=" * 60)
    print("Test 2: Calibration with trained model")
    print("=" * 60)
    
    # Try to load trained model
    model_path = "layer2/trained_model.pkl"
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        set_model(model)
        print(f"✅ Loaded trained model from {model_path}")
    except FileNotFoundError:
        print(f"⚠️  Model not found at {model_path}")
        print("   Run train_model.py first to train a model")
        print("   Skipping this test...\n")
        return
    
    # Test calibration for different restaurants
    test_cases = [
        {
            "name": "McDonald's Big Mac",
            "restaurant": "McDonald's",
            "baseline": BaselineEstimate(
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
        },
        {
            "name": "Subway Sandwich",
            "restaurant": "Subway",
            "baseline": BaselineEstimate(
                item_name="Turkey Sandwich",
                ingredients=["turkey", "bread", "lettuce", "tomato"],
                cooking_methods=["raw"],  # Cold sandwich
                sauces=["mayo"],
                portion_class="entree",
                macros={
                    "calories": 350.0,
                    "fat": 10.0,
                    "carbs": 40.0,
                    "protein": 25.0,
                    "sodium": 800.0
                }
            )
        },
        {
            "name": "Pizza Slice",
            "restaurant": "Domino's",
            "baseline": BaselineEstimate(
                item_name="Pepperoni Pizza",
                ingredients=["dough", "cheese", "pepperoni"],
                cooking_methods=["baked"],
                sauces=["tomato sauce"],
                portion_class="entree",
                macros={
                    "calories": 300.0,
                    "fat": 12.0,
                    "carbs": 35.0,
                    "protein": 15.0,
                    "sodium": 600.0
                }
            )
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📊 Testing: {test_case['name']}")
        result = calibrate(
            baseline_estimate=test_case['baseline'],
            restaurant_metadata={"restaurant": test_case['restaurant']}
        )
        
        print(f"   Restaurant: {test_case['restaurant']}")
        print(f"   Baseline calories: {test_case['baseline']['macros']['calories']:.1f}")
        print(f"   Adjusted calories: {result['adjusted_macros']['calories']:.1f}")
        print(f"   Multiplier: {result['applied_adjustments']['calories']['multiplier']:.3f}")
        print(f"   Adjustment type: {result['applied_adjustments']['calories']['adjustment_type']}")
        print(f"   Confidence: {result['confidence']['calories']:.2f}")
        
        # Verify structure
        assert 'adjusted_macros' in result
        assert 'confidence' in result
        assert 'applied_adjustments' in result
        assert all(macro in result['adjusted_macros'] for macro in ['calories', 'fat', 'carbs', 'protein', 'sodium'])
        assert all(0.0 <= conf <= 1.0 for conf in result['confidence'].values())
    
    print("\n✅ All tests passed!")


def test_feature_extraction():
    """Test feature extraction."""
    print("\n" + "=" * 60)
    print("Test 3: Feature Extraction")
    print("=" * 60)
    
    from .feature_extraction import extract_features
    
    baseline = BaselineEstimate(
        item_name="Test Item",
        ingredients=["test"],
        cooking_methods=["fried", "grilled"],
        sauces=["mayo", "ketchup"],
        portion_class="entree",
        macros={"calories": 100.0, "fat": 10.0, "carbs": 20.0, "protein": 5.0, "sodium": 200.0}
    )
    
    features = extract_features(baseline, {"restaurant": "McDonald's"})
    
    print(f"✅ Features extracted:")
    print(f"   Restaurant: {features['restaurant']}")
    print(f"   Cuisine: {features['cuisine']}")
    print(f"   Cooking methods: {features['cooking_methods']}")
    print(f"   Oil intensity: {features['oil_intensity']}")
    print(f"   Sauce level: {features['sauce_level']}")
    print(f"   Processing level: {features['processing_level']}")
    print(f"   Portion class: {features['portion_class']}")
    print(f"   Price bucket: {features['price_bucket']}")
    
    assert features['restaurant'] == "McDonald's"
    assert features['cuisine'] in ['american', 'fast_food'] or 'american' in features['cuisine'].lower()
    assert len(features['cooking_methods']) > 0
    print("✅ Feature extraction test passed!\n")


if __name__ == "__main__":
    print("\n🧪 Layer 2 Integration Tests\n")
    
    # Run tests
    test_without_model()
    test_feature_extraction()
    test_with_model()
    
    print("\n" + "=" * 60)
    print("✅ All integration tests completed!")
    print("=" * 60)
