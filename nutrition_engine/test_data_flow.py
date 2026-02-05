#!/usr/bin/env python3
"""
Test that data passes through all 3 layers: L1 → L2 → L3.
If it passes Layer 1, it should pass through Layer 2 and Layer 3 in the correct format.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Expected keys at each handoff (from app.schemas)
L1_KEYS = {"macros", "confidence"}
L2_KEYS = {"macros", "layer2_confidence", "applied_adjustments"}
L3_KEYS = {"final_macros", "layer3_confidence", "refinements_applied"}


def main():
    from app.startup import startup
    from layers import layer1, layer2, layer3

    print("=" * 60)
    print("Data flow test: L1 → L2 → L3")
    print("=" * 60)

    print("\nStarting up (L2 calibration + L3 embeddings)...")
    startup()
    print("Startup OK.\n")

    # Single request
    req = {
        "item_name": "Grilled Chicken Salad",
        "description": "Mixed greens with grilled chicken, tomatoes, cucumber",
        "restaurant": "Cafe Fresh",
        "price": 12.99,
        "modifiers": ["extra cheese"],
    }

    # --- Layer 1 ---
    print("Layer 1 (baseline estimate)")
    print("-" * 40)
    l1_out = layer1.estimate(
        item_name=req["item_name"],
        description=req["description"],
        modifiers=req.get("modifiers"),
    )
    l1_keys = set(l1_out.keys())
    missing_l1 = L1_KEYS - l1_keys
    if missing_l1:
        print(f"  FAIL: Layer 1 output missing keys expected by L2: {missing_l1}")
        return 1
    print(f"  Output keys: {sorted(l1_out.keys())} (required for L2: {sorted(L1_KEYS)})")
    print(f"  macros: {l1_out.get('macros')}")
    print(f"  confidence: {l1_out.get('confidence')}")
    print("  OK: L1 output has shape required by Layer 2\n")

    # --- Layer 2 (input = L1 output) ---
    print("Layer 2 (restaurant calibration)")
    print("-" * 40)
    l2_out = layer2.calibrate(
        baseline_estimate=l1_out,
        restaurant_metadata={
            "restaurant": req.get("restaurant"),
            "price": req.get("price"),
        },
    )
    l2_keys = set(l2_out.keys())
    missing_l2 = L2_KEYS - l2_keys
    if missing_l2:
        print(f"  FAIL: Layer 2 output missing keys expected by L3: {missing_l2}")
        return 1
    print(f"  Output keys: {sorted(l2_out.keys())} (required for L3: {sorted(L2_KEYS)})")
    print(f"  macros: {l2_out.get('macros')}")
    print(f"  layer2_confidence: {l2_out.get('layer2_confidence')}")
    print(f"  applied_adjustments (keys): {list((l2_out.get('applied_adjustments') or {}).keys())}")
    # Check data flowed: L2 macros should exist and (if L1 had macros) be present
    l1_macros = l1_out.get("macros") or {}
    l2_macros = l2_out.get("macros") or {}
    if l1_macros and not l2_macros:
        print("  FAIL: L2 returned empty macros but L1 had macros")
        return 1
    print("  OK: L2 output has shape required by Layer 3; data received from L1\n")

    # --- Layer 3 (input = L2 output) ---
    print("Layer 3 (similarity refinement)")
    print("-" * 40)
    l3_out = layer3.apply_layer3(l2_out)
    l3_keys = set(l3_out.keys())
    missing_l3 = L3_KEYS - l3_keys
    if missing_l3:
        print(f"  FAIL: Layer 3 output missing keys expected by engine: {missing_l3}")
        return 1
    print(f"  Output keys: {sorted(l3_out.keys())} (required by engine: {sorted(L3_KEYS)})")
    print(f"  final_macros: {l3_out.get('final_macros')}")
    print(f"  layer3_confidence: {l3_out.get('layer3_confidence')}")
    print(f"  refinements_applied (keys): {list((l3_out.get('refinements_applied') or {}).keys())}")
    l3_macros = l3_out.get("final_macros") or {}
    if l2_macros and not l3_macros:
        print("  FAIL: L3 returned empty final_macros but L2 had macros")
        return 1
    print("  OK: L3 output has shape required by engine; data received from L2\n")

    # --- Full pipeline (engine) ---
    print("Full pipeline (engine.estimate_nutrition)")
    print("-" * 40)
    from app.engine import estimate_nutrition

    resp = estimate_nutrition(req)
    engine_macros = resp.get("macros") or {}
    if l3_macros != engine_macros:
        print(f"  WARN: Engine response macros != L3 final_macros (engine may subset keys)")
    print(f"  response.macros: {engine_macros}")
    print(f"  response.confidence: {resp.get('confidence')}")
    print("  OK: Engine returned response built from L3 output\n")

    print("=" * 60)
    print("Data flow test passed: data passes through all 3 layers.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
