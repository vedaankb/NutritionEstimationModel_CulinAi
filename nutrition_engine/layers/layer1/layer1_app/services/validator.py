"""Sanity check and validation for nutrient calculations."""

from typing import List, Optional

from layer1_app.core.logging import logger
from layer1_app.schemas.recipe import NutrientTotals, ValidationResult, ParsedIngredient


class NutrientValidator:
    """Validate nutrient calculations for consistency."""
    
    # Calorie coefficients (Atwater factors)
    PROTEIN_CALORIES_PER_G = 4.0
    CARB_CALORIES_PER_G = 4.0
    FAT_CALORIES_PER_G = 9.0
    
    # Validation thresholds
    CALORIE_DELTA_THRESHOLD = 0.10  # 10% difference allowed
    MASS_RATIO_THRESHOLD = 1.5  # Nutrients shouldn't exceed 150% of total mass
    LOW_CONFIDENCE_THRESHOLD = 0.7
    
    @staticmethod
    def validate(
        totals: NutrientTotals,
        parsed_ingredients: List[ParsedIngredient],
        total_mass_g: float
    ) -> ValidationResult:
        """
        Validate nutrient totals for physical consistency.
        
        Args:
            totals: Calculated nutrient totals
            parsed_ingredients: List of parsed ingredients
            total_mass_g: Total mass of all ingredients
        
        Returns:
            ValidationResult with checks and warnings
        """
        warnings = []
        errors = []
        
        # Calorie check (4/4/9 rule)
        calorie_check_result = NutrientValidator._check_calories(totals)
        calorie_check_passed = calorie_check_result["passed"]
        calculated_calories = calorie_check_result.get("calculated_calories")
        macros_calories = calorie_check_result.get("macros_calories")
        calorie_delta_percent = calorie_check_result.get("delta_percent")
        
        if not calorie_check_passed:
            warnings.append(calorie_check_result["message"])
        
        # Mass check
        mass_check_result = NutrientValidator._check_mass(totals, total_mass_g)
        mass_check_passed = mass_check_result["passed"]
        
        if not mass_check_passed:
            warnings.append(mass_check_result["message"])
        
        # Check for missing nutrients
        missing_nutrients = NutrientValidator._check_missing_nutrients(totals)
        if missing_nutrients:
            warnings.append(f"Missing nutrients: {', '.join(missing_nutrients)}")
        
        # Check ingredient confidence
        low_confidence = [
            ing for ing in parsed_ingredients 
            if ing.confidence < NutrientValidator.LOW_CONFIDENCE_THRESHOLD
        ]
        
        if low_confidence:
            ing_names = [ing.ingredient_name for ing in low_confidence]
            warnings.append(
                f"Low confidence ingredients: {', '.join(ing_names)}"
            )
        
        # Check for parsing warnings
        parsing_warnings = []
        for ing in parsed_ingredients:
            parsing_warnings.extend(ing.warnings)
        
        if parsing_warnings:
            warnings.extend(parsing_warnings)
        
        # Log validation results
        if warnings or errors:
            logger.info(f"Validation completed with {len(warnings)} warnings, {len(errors)} errors")
        
        return ValidationResult(
            calorie_check_passed=calorie_check_passed,
            calorie_delta_percent=calorie_delta_percent,
            calculated_calories=calculated_calories,
            macros_calories=macros_calories,
            mass_check_passed=mass_check_passed,
            warnings=warnings,
            errors=errors
        )
    
    @staticmethod
    def _check_calories(totals: NutrientTotals) -> dict:
        """
        Check if calculated calories match macronutrient-derived calories.
        
        Uses Atwater factors: protein=4, carbs=4, fat=9 kcal/g
        """
        if totals.calories is None:
            return {
                "passed": True,
                "message": "No calorie data to validate"
            }
        
        # Calculate calories from macros
        protein_cal = (totals.protein_g or 0) * NutrientValidator.PROTEIN_CALORIES_PER_G
        carb_cal = (totals.carbohydrates_g or 0) * NutrientValidator.CARB_CALORIES_PER_G
        fat_cal = (totals.fat_g or 0) * NutrientValidator.FAT_CALORIES_PER_G
        
        macros_calories = protein_cal + carb_cal + fat_cal
        calculated_calories = totals.calories
        
        # Calculate delta
        if macros_calories == 0:
            return {
                "passed": False,
                "message": "No macronutrient data available for calorie validation",
                "calculated_calories": calculated_calories,
                "macros_calories": macros_calories
            }
        
        delta = abs(calculated_calories - macros_calories)
        delta_percent = delta / macros_calories
        
        passed = delta_percent <= NutrientValidator.CALORIE_DELTA_THRESHOLD
        
        message = (
            f"Calorie check: {calculated_calories:.1f} kcal (calculated) vs "
            f"{macros_calories:.1f} kcal (from macros), delta: {delta_percent*100:.1f}%"
        )
        
        if not passed:
            message = f"⚠️ {message} - exceeds {NutrientValidator.CALORIE_DELTA_THRESHOLD*100}% threshold"
        
        return {
            "passed": passed,
            "message": message,
            "calculated_calories": calculated_calories,
            "macros_calories": macros_calories,
            "delta_percent": delta_percent * 100
        }
    
    @staticmethod
    def _check_mass(totals: NutrientTotals, total_mass_g: float) -> dict:
        """
        Check if sum of nutrients is physically reasonable.
        
        The sum of macronutrients shouldn't greatly exceed total mass.
        """
        if total_mass_g == 0:
            return {
                "passed": True,
                "message": "No mass data to validate"
            }
        
        # Sum major macronutrients
        protein_g = totals.protein_g or 0
        carb_g = totals.carbohydrates_g or 0
        fat_g = totals.fat_g or 0
        fiber_g = totals.fiber_g or 0
        
        # Note: We don't include water content, so this is expected to be less than total
        macro_sum = protein_g + carb_g + fat_g + fiber_g
        
        # Check if macros are impossibly high
        ratio = macro_sum / total_mass_g
        
        passed = ratio <= NutrientValidator.MASS_RATIO_THRESHOLD
        
        message = (
            f"Mass check: {macro_sum:.1f}g macros / {total_mass_g:.1f}g total = "
            f"{ratio:.2f} ratio"
        )
        
        if not passed:
            message = f"⚠️ {message} - exceeds {NutrientValidator.MASS_RATIO_THRESHOLD} threshold"
        
        return {
            "passed": passed,
            "message": message
        }
    
    @staticmethod
    def _check_missing_nutrients(totals: NutrientTotals) -> List[str]:
        """Check for important missing nutrients."""
        missing = []
        
        important_nutrients = {
            "protein_g": "Protein",
            "carbohydrates_g": "Carbohydrates",
            "fat_g": "Fat",
            "calories": "Calories"
        }
        
        for field, name in important_nutrients.items():
            value = getattr(totals, field, None)
            if value is None or value == 0:
                missing.append(name)
        
        return missing
