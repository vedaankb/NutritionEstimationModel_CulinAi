"""
Calibration model that learns multipliers from restaurant truth data.
Uses robust statistics (median ratios, trimmed means).
"""

try:
    import numpy as np
except ImportError:
    # Fallback if numpy not available
    class np:
        @staticmethod
        def array(x):
            return list(x)
        @staticmethod
        def mean(x):
            return sum(x) / len(x) if len(x) > 0 else 0
        @staticmethod
        def median(x):
            sorted_x = sorted(x)
            n = len(sorted_x)
            if n == 0:
                return 0
            if n % 2 == 0:
                return (sorted_x[n//2 - 1] + sorted_x[n//2]) / 2
            return sorted_x[n//2]
        @staticmethod
        def std(x):
            if len(x) == 0:
                return 0
            mean = np.mean(x)
            return (sum((xi - mean) ** 2 for xi in x) / len(x)) ** 0.5
        @staticmethod
        def var(x):
            if len(x) == 0:
                return 0
            mean = np.mean(x)
            return sum((xi - mean) ** 2 for xi in x) / len(x)
        @staticmethod
        def sort(x):
            return sorted(x)
        @staticmethod
        def abs(x):
            return abs(x)
        @staticmethod
        def clip(x, min_val, max_val):
            return max(min_val, min(max_val, x))

from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from .schemas import FeatureVector, RestaurantTruth, BaselineEstimate
from .config import (
    DEFAULT_MULTIPLIERS,
    MIN_SAMPLES_FOR_CONFIDENCE,
    TRIMMED_MEAN_PERCENT,
    MEDIAN_FALLBACK_THRESHOLD,
    FALLBACK_ORDER,
)


# Helper functions for picklable defaultdict factories
def _defaultdict_list():
    """Factory function for defaultdict(list) - picklable."""
    return defaultdict(list)


def _defaultdict_int():
    """Factory function for defaultdict(int) - picklable."""
    return defaultdict(int)


class CalibrationModel:
    """
    Learns restaurant-specific multipliers from truth data.
    """
    
    def __init__(self):
        # Multiplier storage: level -> macro -> list of ratios
        # Using helper functions instead of lambdas for pickle compatibility
        self.multipliers = {
            "restaurant": defaultdict(_defaultdict_list),
            "cuisine": defaultdict(_defaultdict_list),
            "cooking_method": defaultdict(_defaultdict_list),
            "sauce_level": defaultdict(_defaultdict_list),
            "portion_class": defaultdict(_defaultdict_list),
            "oil_intensity": defaultdict(_defaultdict_list),
            "processing_level": defaultdict(_defaultdict_list),
        }
        
        # Sample counts for confidence
        self.sample_counts = {
            "restaurant": defaultdict(_defaultdict_int),
            "cuisine": defaultdict(_defaultdict_int),
            "cooking_method": defaultdict(_defaultdict_int),
            "sauce_level": defaultdict(_defaultdict_int),
            "portion_class": defaultdict(_defaultdict_int),
            "oil_intensity": defaultdict(_defaultdict_int),
            "processing_level": defaultdict(_defaultdict_int),
        }
    
    def train(
        self,
        baseline_estimates: List[BaselineEstimate],
        restaurant_truths: List[RestaurantTruth],
        restaurant_metadata: List[Dict],
    ):
        """
        Train the model on paired baseline estimates and truth data.
        
        Args:
            baseline_estimates: List of Layer 1 outputs
            restaurant_truths: List of actual restaurant nutrition data
            restaurant_metadata: List of metadata dicts with 'restaurant' key
        """
        if len(baseline_estimates) != len(restaurant_truths):
            raise ValueError("baseline_estimates and restaurant_truths must have same length")
        
        macros = ["calories", "fat", "carbs", "protein", "sodium"]
        
        for baseline, truth, metadata in zip(baseline_estimates, restaurant_truths, restaurant_metadata):
            restaurant = metadata.get("restaurant", truth.get("chain", "unknown"))
            
            # Extract features
            from .feature_extraction import extract_features
            features = extract_features(baseline, metadata)
            
            # Calculate ratios for each macro
            for macro in macros:
                baseline_val = baseline["macros"].get(macro, 0.0)
                truth_val = truth.get(macro, 0.0)
                
                # Skip if either value is missing or zero
                if baseline_val <= 0 or truth_val <= 0:
                    continue
                
                ratio = truth_val / baseline_val
                
                # Store at different levels
                # Restaurant level
                self.multipliers["restaurant"][restaurant][macro].append(ratio)
                self.sample_counts["restaurant"][restaurant][macro] += 1
                
                # Cuisine level
                self.multipliers["cuisine"][features["cuisine"]][macro].append(ratio)
                self.sample_counts["cuisine"][features["cuisine"]][macro] += 1
                
                # Cooking method level
                for method in features["cooking_methods"]:
                    self.multipliers["cooking_method"][method][macro].append(ratio)
                    self.sample_counts["cooking_method"][method][macro] += 1
                
                # Sauce level
                self.multipliers["sauce_level"][features["sauce_level"]][macro].append(ratio)
                self.sample_counts["sauce_level"][features["sauce_level"]][macro] += 1
                
                # Portion class
                self.multipliers["portion_class"][features["portion_class"]][macro].append(ratio)
                self.sample_counts["portion_class"][features["portion_class"]][macro] += 1
                
                # Oil intensity
                self.multipliers["oil_intensity"][features["oil_intensity"]][macro].append(ratio)
                self.sample_counts["oil_intensity"][features["oil_intensity"]][macro] += 1
                
                # Processing level
                self.multipliers["processing_level"][features["processing_level"]][macro].append(ratio)
                self.sample_counts["processing_level"][features["processing_level"]][macro] += 1
    
    def get_multipliers(self, features: FeatureVector) -> Dict[str, Dict[str, float]]:
        """
        Get multipliers for given features using fallback hierarchy.
        
        Returns:
            Dict mapping macro -> adjustment_type -> multiplier
        """
        macros = ["calories", "fat", "carbs", "protein", "sodium"]
        result = {macro: {} for macro in macros}
        
        # Try each level in fallback order
        for level in FALLBACK_ORDER:
            if level == "default":
                for macro in macros:
                    result[macro][level] = DEFAULT_MULTIPLIERS[macro]
                break
            
            # Get key for this level - level and level_key are the same for most
            level_key = level  # Most levels use the same key
            
            if level == "restaurant":
                key = features["restaurant"]
            elif level == "cuisine":
                key = features["cuisine"]
            elif level == "cooking_method":
                # Use first cooking method
                key = features["cooking_methods"][0] if features["cooking_methods"] else None
            elif level == "sauce_level":
                key = features["sauce_level"]
            elif level == "portion_class":
                key = features["portion_class"]
            elif level == "oil_intensity":
                key = features["oil_intensity"]
            elif level == "processing_level":
                key = features["processing_level"]
            else:
                continue
            
            if key is None:
                continue
            
            # Check if we have data for this level
            has_data = False
            for macro in macros:
                # Use level_key to access the correct multiplier dictionary
                if level_key in self.multipliers:
                    ratios = self.multipliers[level_key].get(key, {}).get(macro, [])
                    if ratios:
                        has_data = True
                        multiplier = self._compute_robust_multiplier(ratios)
                        result[macro][level] = multiplier
            
            # If we found data at this level, use it (don't fall back further)
            if has_data:
                break
        
        return result
    
    def _compute_robust_multiplier(self, ratios: List[float]) -> float:
        """
        Compute robust multiplier from list of ratios.
        Uses trimmed mean if enough samples, median otherwise.
        """
        if not ratios:
            return 1.0
        
        # Convert to list if needed (handles numpy arrays and lists)
        ratios_list = list(ratios) if not isinstance(ratios, list) else ratios
        
        # Remove outliers (beyond 3 standard deviations)
        mean = np.mean(ratios_list)
        std = np.std(ratios_list)
        
        if std > 0:
            # Filter outliers
            filtered_ratios = [
                r for r in ratios_list
                if abs(r - mean) <= 3 * std
            ]
            if filtered_ratios:  # Only use filtered if we have any left
                ratios_list = filtered_ratios
        
        if len(ratios_list) < MEDIAN_FALLBACK_THRESHOLD:
            # Use median for small samples
            return float(np.median(ratios_list))
        
        # Use trimmed mean for larger samples
        trim_count = int(len(ratios_list) * TRIMMED_MEAN_PERCENT)
        if trim_count > 0 and len(ratios_list) > trim_count * 2:
            sorted_ratios = sorted(ratios_list)
            trimmed = sorted_ratios[trim_count:-trim_count]
            return float(np.mean(trimmed))
        
        return float(np.mean(ratios_list))
    
    def get_sample_count(self, features: FeatureVector, macro: str) -> int:
        """Get number of samples backing the multiplier for given features."""
        # Try restaurant level first
        restaurant = features["restaurant"]
        if restaurant in self.sample_counts["restaurant"]:
            count = self.sample_counts["restaurant"][restaurant].get(macro, 0)
            if count > 0:
                return count
        
        # Fall back to cuisine
        cuisine = features["cuisine"]
        if cuisine in self.sample_counts["cuisine"]:
            count = self.sample_counts["cuisine"][cuisine].get(macro, 0)
            if count > 0:
                return count
        
        # Fall back to cooking method
        if features["cooking_methods"]:
            method = features["cooking_methods"][0]
            if method in self.sample_counts["cooking_method"]:
                count = self.sample_counts["cooking_method"][method].get(macro, 0)
                if count > 0:
                    return count
        
        return 0
