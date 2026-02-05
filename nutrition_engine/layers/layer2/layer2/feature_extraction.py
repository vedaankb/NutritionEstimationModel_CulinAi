"""
Deterministic feature extraction from baseline estimates and restaurant metadata.
NO LLM CALLS ALLOWED - rule-based only.
"""

from typing import Dict, List
from .schemas import BaselineEstimate, FeatureVector
from .ontology import (
    normalize_cooking_method,
    normalize_cuisine,
    infer_oil_intensity,
    infer_processing_level,
    SAUCE_LEVELS,
)


def extract_features(
    baseline_estimate: BaselineEstimate,
    restaurant_metadata: Dict
) -> FeatureVector:
    """
    Extract features deterministically from baseline estimate and restaurant metadata.
    
    Args:
        baseline_estimate: Input from Layer 1
        restaurant_metadata: Dict with 'restaurant' (chain name) and optionally 'price'
    
    Returns:
        FeatureVector with all required fields
    """
    restaurant = restaurant_metadata.get("restaurant", "unknown").strip()
    
    # Normalize cooking methods
    cooking_methods = [
        normalize_cooking_method(method)
        for method in baseline_estimate.get("cooking_methods", [])
    ]
    
    # If no cooking methods provided, infer from item name or default
    if not cooking_methods:
        cooking_methods = ["fried"]  # Most common default
    
    # Determine cuisine
    cuisine = normalize_cuisine(restaurant)
    
    # Determine oil intensity
    oil_intensity = infer_oil_intensity(cooking_methods, cuisine)
    
    # Determine sauce level
    sauces = baseline_estimate.get("sauces", [])
    sauce_level = _determine_sauce_level(sauces)
    
    # Determine processing level
    processing_level = infer_processing_level(restaurant, cuisine)
    
    # Portion class (from baseline estimate)
    portion_class = baseline_estimate.get("portion_class", "entree")
    if portion_class not in ["snack", "entree", "platter"]:
        portion_class = "entree"  # Default
    
    # Price bucket (if available)
    price = restaurant_metadata.get("price")
    price_bucket = _determine_price_bucket(price, restaurant)
    
    return FeatureVector(
        restaurant=restaurant,
        cuisine=cuisine,
        cooking_methods=cooking_methods,
        oil_intensity=oil_intensity,
        sauce_level=sauce_level,
        processing_level=processing_level,
        portion_class=portion_class,
        price_bucket=price_bucket,
    )


def _determine_sauce_level(sauces: List[str]) -> str:
    """Determine sauce level from sauce list."""
    if not sauces:
        return "none"
    
    # Count sauces
    sauce_count = len(sauces)
    
    # Check for heavy sauce keywords
    heavy_keywords = ["gravy", "cream", "cheese sauce", "mayo", "ranch", "heavy"]
    has_heavy = any(keyword in sauce.lower() for sauce in sauces 
                    for keyword in heavy_keywords)
    
    if has_heavy or sauce_count >= 3:
        return "heavy"
    elif sauce_count == 2:
        return "medium"
    elif sauce_count == 1:
        return "light"
    else:
        return "none"


def _determine_price_bucket(price: float = None, restaurant: str = "") -> str:
    """Determine price bucket from price or restaurant type."""
    if price is not None:
        if price < 10:
            return "cheap"
        elif price < 20:
            return "mid"
        else:
            return "premium"
    
    # Infer from restaurant type
    restaurant_lower = restaurant.lower()
    
    # Premium restaurants
    premium_keywords = ["five guys", "shake shack", "pf changs", "olive garden", 
                       "red lobster", "outback", "texas roadhouse"]
    if any(kw in restaurant_lower for kw in premium_keywords):
        return "premium"
    
    # Mid-range
    mid_keywords = ["chipotle", "panera", "cava", "panda express", "subway"]
    if any(kw in restaurant_lower for kw in mid_keywords):
        return "mid"
    
    # Cheap (fast food)
    return "cheap"
