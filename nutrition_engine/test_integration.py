#!/usr/bin/env python3
"""Run the 3-layer pipeline in-process. Use this to verify integration without starting the server."""

import sys
import os

# Run from nutrition_engine directory so app and layers are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from app.startup import startup
    from app.engine import estimate_nutrition

    print("Starting up (loading L2 calibration + L3 embeddings)...")
    startup()
    print("Startup OK.\n")

    req = {
        "item_name": "Grilled Chicken Salad",
        "description": "Mixed greens with grilled chicken, tomatoes, cucumber",
        "restaurant": "Cafe Fresh",
        "price": 12.99,
        "modifiers": ["extra cheese"],
    }
    print("Request:", req)
    print("\nRunning pipeline: Layer 1 → Layer 2 → Layer 3...")
    resp = estimate_nutrition(req)
    print("\nResponse:")
    for k, v in resp.items():
        print(f"  {k}: {v}")
    print("\nIntegration test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
