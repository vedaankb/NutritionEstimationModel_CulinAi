"""
Training script for Layer 2 calibration model.

This script:
1. Loads the Part B restaurant nutrition dataset
2. Generates simulated Layer 1 baseline estimates
3. Trains the calibration model
4. Saves the trained model
"""

import pandas as pd
import pickle
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from layer2 import CalibrationModel, set_model
from .schemas import BaselineEstimate, RestaurantTruth


def load_restaurant_data(data_path: str = "data/processed/restaurant_nutrition_dataset.csv"):
    """Load restaurant nutrition data from Part B."""
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}")
    
    df = pd.read_csv(data_path)
    print(f"✅ Loaded {len(df)} rows from {data_path}")
    print(f"   Columns: {', '.join(df.columns[:10])}...")
    
    return df


def create_simulated_baseline(truth_row: pd.Series) -> BaselineEstimate:
    """
    Create a simulated Layer 1 baseline estimate.
    
    In production, this would come from Layer 1.
    For now, we simulate by adding some noise/variation to the truth data.
    """
    # Simulate Layer 1 being ~10-20% off on average
    import random
    noise_factor = random.uniform(0.85, 1.15)  # ±15% variation
    
    # Simulate different accuracies for different macros
    macro_noise = {
        "calories": random.uniform(0.90, 1.10),
        "fat": random.uniform(0.85, 1.15),  # Fat is harder to estimate
        "carbs": random.uniform(0.90, 1.10),
        "protein": random.uniform(0.88, 1.12),
        "sodium": random.uniform(0.80, 1.20),  # Sodium varies a lot
    }
    
    # Infer cooking method from item name
    item_name = str(truth_row.get("item_name", "")).lower()
    cooking_methods = []
    
    if any(word in item_name for word in ["fried", "crispy", "fries"]):
        cooking_methods.append("deep_fried")
    elif any(word in item_name for word in ["grilled", "flame"]):
        cooking_methods.append("grilled")
    elif any(word in item_name for word in ["baked", "oven"]):
        cooking_methods.append("baked")
    elif any(word in item_name for word in ["roasted", "tandoor"]):
        cooking_methods.append("roasted")
    else:
        cooking_methods.append("fried")  # Default
    
    # Infer sauces
    sauces = []
    if any(word in item_name for word in ["sauce", "mayo", "ranch", "dressing"]):
        sauces.append("sauce")
    
    # Infer portion class
    portion_class = "entree"
    if any(word in item_name for word in ["snack", "small", "mini"]):
        portion_class = "snack"
    elif any(word in item_name for word in ["platter", "combo", "large"]):
        portion_class = "platter"
    
    # Get nutrition values
    calories = float(truth_row.get("calories", 0) or 0)
    fat = float(truth_row.get("fat", 0) or 0)
    carbs = float(truth_row.get("carbs", 0) or 0)
    protein = float(truth_row.get("protein", 0) or 0)
    sodium = float(truth_row.get("sodium", 0) or 0)
    
    # Create baseline with noise
    baseline = BaselineEstimate(
        item_name=str(truth_row.get("item_name", "Unknown")),
        ingredients=[],  # Would come from Layer 1
        cooking_methods=cooking_methods,
        sauces=sauces,
        portion_class=portion_class,
        macros={
            "calories": max(0, calories * macro_noise["calories"]),
            "fat": max(0, fat * macro_noise["fat"]),
            "carbs": max(0, carbs * macro_noise["carbs"]),
            "protein": max(0, protein * macro_noise["protein"]),
            "sodium": max(0, sodium * macro_noise["sodium"]),
        }
    )
    
    return baseline


def prepare_training_data(df: pd.DataFrame, max_samples: int = None):
    """
    Prepare training data from restaurant dataset.
    
    Args:
        df: Restaurant nutrition dataframe
        max_samples: Maximum number of samples to use (None = all)
    
    Returns:
        Tuple of (baseline_estimates, restaurant_truths, restaurant_metadata)
    """
    # Filter out rows with missing nutrition data
    required_cols = ["chain", "item_name", "calories", "fat", "carbs", "protein", "sodium"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"⚠️  Missing columns: {missing_cols}")
        print(f"   Available columns: {', '.join(df.columns)}")
        # Try to find similar column names
        for col in missing_cols:
            similar = [c for c in df.columns if col.lower() in c.lower() or c.lower() in col.lower()]
            if similar:
                print(f"   Found similar for '{col}': {similar}")
    
    # Filter valid rows
    valid_rows = df.dropna(subset=["chain", "item_name"])
    
    # Filter rows with at least some nutrition data
    nutrition_cols = ["calories", "fat", "carbs", "protein", "sodium"]
    available_nutrition = [col for col in nutrition_cols if col in df.columns]
    
    if available_nutrition:
        valid_rows = valid_rows.dropna(subset=available_nutrition[:1])  # At least one nutrition value
    
    if max_samples:
        valid_rows = valid_rows.head(max_samples)
    
    print(f"\n📊 Preparing training data:")
    print(f"   Valid rows: {len(valid_rows)}")
    print(f"   Unique chains: {valid_rows['chain'].nunique()}")
    print(f"   Chains: {', '.join(sorted(valid_rows['chain'].unique())[:10])}...")
    
    baseline_estimates = []
    restaurant_truths = []
    restaurant_metadata = []
    
    for _, row in valid_rows.iterrows():
        # Create baseline estimate
        baseline = create_simulated_baseline(row)
        baseline_estimates.append(baseline)
        
        # Create restaurant truth
        truth = RestaurantTruth(
            chain=str(row.get("chain", "Unknown")),
            item_name=str(row.get("item_name", "Unknown")),
            calories=float(row.get("calories", 0) or 0),
            fat=float(row.get("fat", 0) or 0),
            carbs=float(row.get("carbs", 0) or 0),
            protein=float(row.get("protein", 0) or 0),
            sodium=float(row.get("sodium", 0) or 0),
        )
        restaurant_truths.append(truth)
        
        # Create metadata
        restaurant_metadata.append({
            "restaurant": str(row.get("chain", "Unknown"))
        })
    
    return baseline_estimates, restaurant_truths, restaurant_metadata


def train_and_save_model(
    data_path: str = "data/processed/restaurant_nutrition_dataset.csv",
    model_path: str = "layer2/trained_model.pkl",
    max_samples: int = None
):
    """
    Train the calibration model and save it.
    
    Args:
        data_path: Path to restaurant nutrition dataset
        model_path: Path to save trained model
        max_samples: Maximum number of training samples (None = all)
    """
    print("=" * 60)
    print("Layer 2 Model Training")
    print("=" * 60)
    
    # Load data
    df = load_restaurant_data(data_path)
    
    # Prepare training data
    baseline_estimates, restaurant_truths, restaurant_metadata = prepare_training_data(
        df, max_samples=max_samples
    )
    
    if not baseline_estimates:
        raise ValueError("No valid training data found!")
    
    # Train model
    print(f"\n🔧 Training calibration model on {len(baseline_estimates)} samples...")
    model = CalibrationModel()
    model.train(baseline_estimates, restaurant_truths, restaurant_metadata)
    
    # Set as global model
    set_model(model)
    
    # Save model
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"✅ Model trained and saved to {model_path}")
    
    # Print statistics
    print(f"\n📊 Model Statistics:")
    print(f"   Restaurants learned: {len(model.multipliers['restaurant'])}")
    print(f"   Cuisines learned: {len(model.multipliers['cuisine'])}")
    print(f"   Cooking methods learned: {len(model.multipliers['cooking_method'])}")
    
    # Show sample counts for a few restaurants
    print(f"\n   Sample counts (top 5 restaurants):")
    restaurant_counts = {}
    for restaurant, macros in model.sample_counts['restaurant'].items():
        total = sum(macros.values())
        if total > 0:
            restaurant_counts[restaurant] = total
    
    for restaurant, count in sorted(restaurant_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"     {restaurant}: {count} samples")
    
    return model


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Layer 2 calibration model")
    parser.add_argument(
        "--data",
        type=str,
        default="data/processed/restaurant_nutrition_dataset.csv",
        help="Path to restaurant nutrition dataset"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="layer2/trained_model.pkl",
        help="Path to save trained model"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Maximum number of training samples (None = all)"
    )
    
    args = parser.parse_args()
    
    try:
        model = train_and_save_model(
            data_path=args.data,
            model_path=args.output,
            max_samples=args.max_samples
        )
        print("\n✅ Training complete!")
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
