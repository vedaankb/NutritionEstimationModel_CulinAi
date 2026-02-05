"""
Fixed ontology for mapping cooking methods, sauces, and processing levels.
"""

# Allowed cooking methods (from requirements)
COOKING_METHODS = {
    "grilled",
    "fried",
    "deep_fried",
    "baked",
    "roasted",
    "steamed",
    "raw",
    "sauteed",
    "pressure_cooked",
}

# Mapping from common variations to canonical forms
COOKING_METHOD_MAPPING = {
    # Grilled variations
    "grill": "grilled",
    "grilling": "grilled",
    "char-grilled": "grilled",
    "flame-grilled": "grilled",
    "flame grilled": "grilled",
    
    # Fried variations
    "fry": "fried",
    "frying": "fried",
    "pan-fried": "fried",
    "pan fried": "fried",
    "stir-fried": "fried",
    "stir fried": "fried",
    "wok": "fried",  # Wok cooking is typically stir-frying
    "deep-fried": "deep_fried",
    "deep fried": "deep_fried",
    "deepfry": "deep_fried",
    
    # Baked variations
    "bake": "baked",
    "baking": "baked",
    "oven-baked": "baked",
    "oven baked": "baked",
    
    # Roasted variations
    "roast": "roasted",
    "roasting": "roasted",
    
    # Steamed variations
    "steam": "steamed",
    "steaming": "steamed",
    
    # Raw variations
    "raw": "raw",
    "uncooked": "raw",
    
    # Sauteed variations
    "saute": "sauteed",
    "sauté": "sauteed",
    "sautéed": "sauteed",
    
    # Pressure cooked variations
    "pressure-cooked": "pressure_cooked",
    "pressure cooked": "pressure_cooked",
    "pressure cook": "pressure_cooked",
    "tandoor": "roasted",  # Tandoor is a type of roasting
}

# Sauce level mapping
SAUCE_LEVELS = {
    "none": 0,
    "light": 1,
    "medium": 2,
    "heavy": 3,
}

# Processing levels
PROCESSING_LEVELS = {
    "fresh",
    "processed",
    "ultra_processed",
}

# Oil intensity levels
OIL_INTENSITY_LEVELS = {
    "low",
    "medium",
    "high",
}

# Cuisine mapping (common restaurant cuisines)
CUISINE_MAPPING = {
    # American
    "mcdonalds": "american",
    "burger king": "american",
    "wendys": "american",
    "chick-fil-a": "american",
    "chick fil a": "american",
    "arbys": "american",
    "sonic": "american",
    "jack in the box": "american",
    "five guys": "american",
    "shake shack": "american",
    "in-n-out": "american",
    "in n out": "american",
    "dennys": "american",
    "ihop": "american",
    
    # Mexican/Tex-Mex
    "taco bell": "mexican",
    "chipotle": "mexican",
    "qdoba": "mexican",
    "moes": "mexican",
    "moes southwest grill": "mexican",
    
    # Italian
    "dominos": "italian",
    "domino's": "italian",
    "pizza hut": "italian",
    "olive garden": "italian",
    "fazolis": "italian",
    
    # Asian/Chinese
    "panda express": "chinese",
    "pf changs": "chinese",
    "p.f. chang's": "chinese",
    "pei wei": "chinese",
    "kfc": "asian",  # KFC is fried chicken, Asian-style
    
    # Indian
    "curry house": "indian",
    "bombay express": "indian",
    
    # Mediterranean
    "cava": "mediterranean",
    "panera bread": "mediterranean",  # Panera has Mediterranean influences
    
    # Seafood
    "red lobster": "seafood",
    "long john silvers": "seafood",
    
    # Steakhouse
    "outback": "steakhouse",
    "outback steakhouse": "steakhouse",
    "texas roadhouse": "steakhouse",
    
    # Coffee/Café
    "starbucks": "coffee",
    "dunkin": "coffee",
    "dunkin'": "coffee",
    
    # Sandwich/Deli
    "subway": "sandwich",
    "panera bread": "sandwich",  # Also sandwiches
    
    # African/Portuguese
    "nandos": "african",
    "nando's": "african",
    
    # Casual Dining
    "applebees": "american",
    "applebee's": "american",
}


def normalize_cooking_method(method: str) -> str:
    """Normalize cooking method to canonical form."""
    method_lower = method.lower().strip()
    
    # Direct match
    if method_lower in COOKING_METHODS:
        return method_lower
    
    # Check mapping
    if method_lower in COOKING_METHOD_MAPPING:
        return COOKING_METHOD_MAPPING[method_lower]
    
    # Partial match
    for key, value in COOKING_METHOD_MAPPING.items():
        if key in method_lower or method_lower in key:
            return value
    
    # Default to most common if unclear
    return "fried"  # Most common in fast food


def normalize_cuisine(restaurant: str) -> str:
    """Map restaurant name to cuisine type."""
    restaurant_lower = restaurant.lower().strip()
    
    # Remove common suffixes
    restaurant_lower = restaurant_lower.replace(" (pdf)", "").replace(" (html)", "")
    
    # Direct match
    if restaurant_lower in CUISINE_MAPPING:
        return CUISINE_MAPPING[restaurant_lower]
    
    # Partial match
    for key, value in CUISINE_MAPPING.items():
        if key in restaurant_lower:
            return value
    
    # Default
    return "american"


def infer_oil_intensity(cooking_methods: list, cuisine: str) -> str:
    """Infer oil intensity from cooking methods and cuisine."""
    if not cooking_methods:
        return "medium"
    
    methods_lower = [m.lower() for m in cooking_methods]
    
    # High oil intensity
    if any(m in ["deep_fried", "fried"] for m in methods_lower):
        return "high"
    
    # Medium oil intensity
    if any(m in ["sauteed", "roasted", "baked"] for m in methods_lower):
        return "medium"
    
    # Low oil intensity
    if any(m in ["steamed", "raw", "grilled"] for m in methods_lower):
        return "low"
    
    return "medium"


def infer_processing_level(restaurant: str, cuisine: str) -> str:
    """Infer processing level from restaurant and cuisine."""
    restaurant_lower = restaurant.lower()
    
    # Fast food chains are typically ultra-processed
    fast_food_keywords = ["mcdonalds", "burger king", "wendys", "taco bell", "kfc", 
                         "pizza hut", "dominos", "subway", "dunkin"]
    
    if any(kw in restaurant_lower for kw in fast_food_keywords):
        return "ultra_processed"
    
    # Casual dining is typically processed
    casual_keywords = ["olive garden", "applebees", "red lobster", "outback", 
                      "texas roadhouse", "dennys", "ihop"]
    
    if any(kw in restaurant_lower for kw in casual_keywords):
        return "processed"
    
    # Premium/fast-casual is typically fresh
    premium_keywords = ["five guys", "shake shack", "chipotle", "cava", "panera"]
    
    if any(kw in restaurant_lower for kw in premium_keywords):
        return "fresh"
    
    return "processed"  # Default
