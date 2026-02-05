"""
Monitor confidence scores and identify low-quality adjustments.

This script analyzes the calibration model to identify:
- Low confidence adjustments
- Restaurants with insufficient data
- Macros with high variance
"""

import sys
from pathlib import Path
import pickle
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from layer2 import CalibrationModel
from .confidence import confidence_score
from .schemas import FeatureVector


def analyze_model_confidence(model_path: str = "layer2/trained_model.pkl"):
    """Analyze confidence scores across the model."""
    print("=" * 60)
    print("Layer 2 Confidence Analysis")
    print("=" * 60)
    
    # Load model
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        print(f"✅ Loaded model from {model_path}\n")
    except FileNotFoundError:
        print(f"❌ Model not found at {model_path}")
        print("   Run train_model.py first")
        return
    
    # Analyze sample counts
    print("📊 Sample Count Analysis:")
    print("-" * 60)
    
    restaurant_counts = defaultdict(int)
    for restaurant, macros in model.sample_counts['restaurant'].items():
        total = sum(macros.values())
        restaurant_counts[restaurant] = total
    
    # Sort by count
    sorted_restaurants = sorted(restaurant_counts.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n   Restaurants with most samples:")
    for restaurant, count in sorted_restaurants[:10]:
        print(f"     {restaurant:30s}: {count:4d} samples")
    
    print(f"\n   Restaurants with few samples (< 5):")
    low_sample_restaurants = [(r, c) for r, c in sorted_restaurants if c < 5]
    if low_sample_restaurants:
        for restaurant, count in low_sample_restaurants:
            print(f"     {restaurant:30s}: {count:4d} samples ⚠️")
    else:
        print("     None")
    
    # Analyze confidence for sample restaurants
    print(f"\n📈 Confidence Score Analysis:")
    print("-" * 60)
    
    test_restaurants = [r for r, _ in sorted_restaurants[:5]]
    
    for restaurant in test_restaurants:
        print(f"\n   Restaurant: {restaurant}")
        
        # Create sample features
        features = FeatureVector(
            restaurant=restaurant,
            cuisine="american",  # Will be normalized
            cooking_methods=["fried"],
            oil_intensity="high",
            sauce_level="medium",
            processing_level="ultra_processed",
            portion_class="entree",
            price_bucket="cheap"
        )
        
        # Get confidence for each macro
        macros = ["calories", "fat", "carbs", "protein", "sodium"]
        confidences = {}
        for macro in macros:
            conf = confidence_score(model, features, macro)
            confidences[macro] = conf
        
        avg_confidence = sum(confidences.values()) / len(confidences)
        
        print(f"     Average confidence: {avg_confidence:.2f}")
        print(f"     Per macro:")
        for macro, conf in confidences.items():
            status = "✅" if conf >= 0.7 else "⚠️" if conf >= 0.4 else "❌"
            print(f"       {macro:10s}: {conf:.2f} {status}")
    
    # Analyze multiplier variance
    print(f"\n📉 Multiplier Variance Analysis:")
    print("-" * 60)
    
    high_variance_restaurants = []
    for restaurant, macros in model.multipliers['restaurant'].items():
        for macro, ratios in macros.items():
            if len(ratios) >= 5:
                import numpy as np
                variance = np.var(ratios)
                if variance > 0.1:  # High variance threshold
                    high_variance_restaurants.append((restaurant, macro, variance, len(ratios)))
    
    if high_variance_restaurants:
        print(f"\n   Restaurants with high variance (> 0.1):")
        for restaurant, macro, variance, count in sorted(high_variance_restaurants, key=lambda x: x[2], reverse=True)[:10]:
            print(f"     {restaurant:30s} {macro:10s}: variance={variance:.3f} (n={count})")
    else:
        print("     No high variance found")
    
    # Summary
    print(f"\n📋 Summary:")
    print("-" * 60)
    print(f"   Total restaurants: {len(model.multipliers['restaurant'])}")
    print(f"   Total cuisines: {len(model.multipliers['cuisine'])}")
    print(f"   Total cooking methods: {len(model.multipliers['cooking_method'])}")
    print(f"   Restaurants with < 5 samples: {len(low_sample_restaurants)}")
    print(f"   High variance cases: {len(high_variance_restaurants)}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    print("-" * 60)
    if low_sample_restaurants:
        print(f"   ⚠️  Add more data for {len(low_sample_restaurants)} restaurants")
    if high_variance_restaurants:
        print(f"   ⚠️  Review {len(high_variance_restaurants)} high-variance cases")
    if not low_sample_restaurants and not high_variance_restaurants:
        print(f"   ✅ Model looks good! All restaurants have sufficient data.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor Layer 2 confidence scores")
    parser.add_argument(
        "--model",
        type=str,
        default="layer2/trained_model.pkl",
        help="Path to trained model"
    )
    
    args = parser.parse_args()
    
    analyze_model_confidence(args.model)
