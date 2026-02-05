"""
Example usage of Layer 2 calibration engine.

This demonstrates how to:
1. Train the model on restaurant data
2. Use it to calibrate Layer 1 baseline estimates
"""

import pandas as pd
from layer2 import CalibrationModel, calibrate, set_model
from .schemas import BaselineEstimate, RestaurantTruth


def example_training():
    """Example: Train the model on restaurant data."""
    
    # Load restaurant nutrition data (from Part B)
    # This is a simplified example - in practice, load from your dataset
    restaurant_data = pd.read_csv("data/processed/restaurant_nutrition_dataset.csv")
    
    # For this example, we'll create dummy baseline estimates
    # In practice, these would come from Layer 1
    baseline_estimates = []
    restaurant_truths = []
    restaurant_metadata = []
    
    # Process each row
    for _, row in restaurant_data.head(100).iterrows():  # Use first 100 for example
        # Create baseline estimate (simulated - in practice from Layer 1)
        baseline = BaselineEstimate(
            item_name=row.get("item_name", "Unknown"),
            ingredients=[],  # Would come from Layer 1
            cooking_methods=["fried"],  # Would come from Layer 1
            sauces=[],
            portion_class="entree",
            macros={
                "calories": row.get("calories", 0) * 0.9,  # Simulate 10% lower baseline
                "fat": row.get("fat", 0) * 0.9,
                "carbs": row.get("carbs", 0) * 0.9,
                "protein": row.get("protein", 0) * 0.9,
                "sodium": row.get("sodium", 0) * 0.9,
            }
        )
        
        # Create restaurant truth
        truth = RestaurantTruth(
            chain=row.get("chain", "Unknown"),
            item_name=row.get("item_name", "Unknown"),
            calories=float(row.get("calories", 0)),
            fat=float(row.get("fat", 0)),
            carbs=float(row.get("carbs", 0)),
            protein=float(row.get("protein", 0)),
            sodium=float(row.get("sodium", 0)),
        )
        
        baseline_estimates.append(baseline)
        restaurant_truths.append(truth)
        restaurant_metadata.append({"restaurant": row.get("chain", "Unknown")})
    
    # Train model
    model = CalibrationModel()
    model.train(baseline_estimates, restaurant_truths, restaurant_metadata)
    
    # Set as global model
    set_model(model)
    
    print("✅ Model trained successfully!")
    return model


def example_inference():
    """Example: Use the model to calibrate a baseline estimate."""
    
    # Example baseline from Layer 1
    baseline = BaselineEstimate(
        item_name="Big Mac",
        ingredients=["beef patty", "bun", "cheese", "lettuce", "pickles", "onions"],
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
    
    print("\n📊 Calibration Results:")
    print(f"  Item: {baseline['item_name']}")
    print(f"  Restaurant: McDonald's")
    print("\n  Adjusted Macros:")
    for macro, value in result["adjusted_macros"].items():
        baseline_val = baseline["macros"][macro]
        multiplier = result["applied_adjustments"][macro]["multiplier"]
        confidence = result["confidence"][macro]
        print(f"    {macro:10s}: {baseline_val:7.1f} → {value:7.1f} "
              f"(×{multiplier:.2f}, conf={confidence:.2f})")
    
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Layer 2 Calibration Engine - Example Usage")
    print("=" * 60)
    
    # Train model (if data available)
    try:
        model = example_training()
    except FileNotFoundError:
        print("⚠️  Dataset not found. Skipping training.")
        print("   Create a model manually for inference example.")
        model = None
    
    # Run inference example
    print("\n" + "=" * 60)
    example_inference()
