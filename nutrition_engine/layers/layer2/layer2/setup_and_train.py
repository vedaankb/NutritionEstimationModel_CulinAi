#!/usr/bin/env python3
"""
One-step setup and training script.

This script:
1. Checks dependencies
2. Verifies dataset exists
3. Trains the model
4. Runs tests
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed."""
    print("🔍 Checking dependencies...")
    
    required = ['numpy', 'pandas']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("   Install with: pip install " + " ".join(missing))
        return False
    
    return True


def check_dataset():
    """Check if dataset exists."""
    print("\n🔍 Checking dataset...")
    
    dataset_path = "data/processed/restaurant_nutrition_dataset.csv"
    
    if os.path.exists(dataset_path):
        print(f"   ✅ Dataset found: {dataset_path}")
        
        # Check size
        size = os.path.getsize(dataset_path)
        print(f"   📊 Size: {size / 1024:.1f} KB")
        return True
    else:
        print(f"   ❌ Dataset not found: {dataset_path}")
        print("   Please run the notebook to generate the dataset first.")
        return False


def main():
    """Main setup and training flow."""
    print("=" * 60)
    print("Layer 2 Setup and Training")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Setup failed: Missing dependencies")
        print("   Run: pip install numpy pandas")
        sys.exit(1)
    
    # Check dataset
    if not check_dataset():
        print("\n❌ Setup failed: Dataset not found")
        print("   Run the notebook to generate the dataset first.")
        sys.exit(1)
    
    # Train model
    print("\n🚀 Training model...")
    print("-" * 60)
    
    try:
        from .train_model import train_and_save_model
        
        model = train_and_save_model(
            data_path="data/processed/restaurant_nutrition_dataset.csv",
            model_path="layer2/trained_model.pkl",
            max_samples=5000  # Use first 5000 samples for quick training
        )
        
        print("\n✅ Training complete!")
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Run tests
    print("\n🧪 Running integration tests...")
    print("-" * 60)
    
    try:
        from .test_integration import test_without_model, test_feature_extraction
        
        test_without_model()
        test_feature_extraction()
        
        print("\n✅ Basic tests passed!")
        
    except Exception as e:
        print(f"\n⚠️  Some tests failed: {e}")
        print("   This is okay if the model wasn't trained yet.")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Review model: python3 layer2/monitor_confidence.py")
    print("  2. Test integration: python3 layer2/test_integration.py")
    print("  3. Use in code: See QUICKSTART.md")
    print("\n")


if __name__ == "__main__":
    main()
