"""Core nutrient calculation engine."""

from collections import defaultdict
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from layer1_app.core.logging import logger
from layer1_app.db.models import (
    FoodNutrient, USDAFood, Nutrient, RetentionFactor, CookingMethod
)
from layer1_app.schemas.recipe import ParsedIngredient, NutrientContribution, NutrientTotals


class NutrientCalculator:
    """Calculate nutrients for recipes with retention factors."""
    
    # Default retention factors when specific ones not available
    DEFAULT_RETENTION = 0.90
    
    # Nutrient ID mappings (to be populated from database)
    NUTRIENT_MAPPINGS = {
        "Energy": "calories",
        "Protein": "protein_g",
        "Carbohydrate, by difference": "carbohydrates_g",
        "Total lipid (fat)": "fat_g",
        "Fiber, total dietary": "fiber_g",
        "Sugars, total including NLEA": "sugar_g",
        "Vitamin A, RAE": "vitamin_a_mcg",
        "Vitamin C, total ascorbic acid": "vitamin_c_mg",
        "Vitamin D (D2 + D3)": "vitamin_d_mcg",
        "Vitamin E (alpha-tocopherol)": "vitamin_e_mg",
        "Vitamin K (phylloquinone)": "vitamin_k_mcg",
        "Thiamin": "thiamin_mg",
        "Riboflavin": "riboflavin_mg",
        "Niacin": "niacin_mg",
        "Vitamin B-6": "vitamin_b6_mg",
        "Folate, total": "folate_mcg",
        "Vitamin B-12": "vitamin_b12_mcg",
        "Calcium, Ca": "calcium_mg",
        "Iron, Fe": "iron_mg",
        "Magnesium, Mg": "magnesium_mg",
        "Phosphorus, P": "phosphorus_mg",
        "Potassium, K": "potassium_mg",
        "Sodium, Na": "sodium_mg",
        "Zinc, Zn": "zinc_mg",
    }
    
    def __init__(self, db: Session):
        """Initialize calculator with database session."""
        self.db = db
        self._nutrient_cache: Dict[int, Nutrient] = {}
        self._cooking_method_cache: Dict[str, CookingMethod] = {}
    
    def calculate_recipe(
        self,
        parsed_ingredients: List[ParsedIngredient],
        cooking_method: Optional[str] = None
    ) -> Tuple[NutrientTotals, List[NutrientContribution]]:
        """
        Calculate total nutrients for a recipe.
        
        Args:
            parsed_ingredients: List of parsed ingredients with mass
            cooking_method: Cooking method (e.g., 'baked', 'boiled')
        
        Returns:
            Tuple of (NutrientTotals, audit_trail)
        """
        totals: Dict[str, float] = defaultdict(float)
        audit_trail: List[NutrientContribution] = []
        
        # Get cooking method from database
        cooking_method_obj = None
        if cooking_method:
            cooking_method_obj = self._get_cooking_method(cooking_method)
        
        for ingredient in parsed_ingredients:
            if not ingredient.ingredient_id:
                logger.warning(
                    f"Ingredient '{ingredient.ingredient_name}' not matched, skipping"
                )
                continue
            
            # Get nutrient profile
            nutrient_profile = self._get_nutrient_profile(
                ingredient.ingredient_id,
                cooking_method_obj
            )
            
            if not nutrient_profile:
                logger.warning(
                    f"No nutrient profile for ingredient {ingredient.ingredient_name}"
                )
                continue
            
            # Calculate contribution for each nutrient
            for nutrient_id, (amount_per_100g, fdc_id) in nutrient_profile.items():
                nutrient = self._get_nutrient(nutrient_id)
                
                # Get retention factor
                retention = self._get_retention_factor(
                    nutrient_id, cooking_method_obj
                )
                
                # Calculate contribution
                raw_contribution = (ingredient.mass_g / 100.0) * amount_per_100g
                final_contribution = raw_contribution * retention
                
                # Add to totals
                nutrient_key = self._get_nutrient_key(nutrient.name)
                if nutrient_key:
                    totals[nutrient_key] += final_contribution
                else:
                    totals[f"other_{nutrient.name}"] = (
                        totals.get(f"other_{nutrient.name}", 0.0) + final_contribution
                    )
                
                # Add to audit trail
                audit_trail.append(NutrientContribution(
                    ingredient_name=ingredient.ingredient_name,
                    mass_g=ingredient.mass_g,
                    nutrient_name=nutrient.name,
                    nutrient_unit=nutrient.unit,
                    raw_contribution=raw_contribution,
                    retention_factor=retention,
                    final_contribution=final_contribution,
                    source_fdc_id=fdc_id
                ))
        
        # Convert totals dict to NutrientTotals object
        nutrient_totals = self._build_nutrient_totals(totals)
        
        return nutrient_totals, audit_trail
    
    def _get_nutrient_profile(
        self,
        ingredient_id: int,
        cooking_method: Optional[CookingMethod]
    ) -> Dict[int, Tuple[float, int]]:
        """
        Get nutrient profile for an ingredient.
        
        Returns dict of {nutrient_id: (amount_per_100g, fdc_id)}
        """
        profile: Dict[int, Tuple[float, int]] = {}
        
        # Get USDA foods for this ingredient
        usda_foods = self.db.query(USDAFood).filter(
            USDAFood.ingredient_id == ingredient_id
        ).all()
        
        if not usda_foods:
            return profile
        
        # Prefer cooked variant if cooking method specified
        selected_food = None
        
        if cooking_method:
            # Look for matching cooking state
            for food in usda_foods:
                if food.cooking_state and cooking_method.name.lower() in food.cooking_state.lower():
                    selected_food = food
                    break
        
        # Fall back to raw or first available
        if not selected_food:
            for food in usda_foods:
                if food.cooking_state and "raw" in food.cooking_state.lower():
                    selected_food = food
                    break
            
            if not selected_food and usda_foods:
                selected_food = usda_foods[0]
        
        if not selected_food:
            return profile
        
        # Get nutrients for this food
        food_nutrients = self.db.query(FoodNutrient).filter(
            FoodNutrient.fdc_id == selected_food.fdc_id
        ).all()
        
        for fn in food_nutrients:
            profile[fn.nutrient_id] = (fn.amount_per_100g, selected_food.fdc_id)
        
        return profile
    
    def _get_retention_factor(
        self,
        nutrient_id: int,
        cooking_method: Optional[CookingMethod]
    ) -> float:
        """Get retention factor for a nutrient and cooking method."""
        if not cooking_method:
            return 1.0
        
        retention = self.db.query(RetentionFactor).filter(
            RetentionFactor.nutrient_id == nutrient_id,
            RetentionFactor.cooking_method_id == cooking_method.id
        ).first()
        
        if retention:
            return retention.retention_factor
        
        # Return default retention
        return self.DEFAULT_RETENTION
    
    def _get_nutrient(self, nutrient_id: int) -> Nutrient:
        """Get nutrient from cache or database."""
        if nutrient_id not in self._nutrient_cache:
            nutrient = self.db.query(Nutrient).filter(
                Nutrient.id == nutrient_id
            ).first()
            if nutrient:
                self._nutrient_cache[nutrient_id] = nutrient
        
        return self._nutrient_cache.get(nutrient_id)
    
    def _get_cooking_method(self, method_name: str) -> Optional[CookingMethod]:
        """Get cooking method from cache or database."""
        method_lower = method_name.lower()
        
        if method_lower not in self._cooking_method_cache:
            method = self.db.query(CookingMethod).filter(
                CookingMethod.name.ilike(f"%{method_lower}%")
            ).first()
            
            if method:
                self._cooking_method_cache[method_lower] = method
        
        return self._cooking_method_cache.get(method_lower)
    
    def _get_nutrient_key(self, nutrient_name: str) -> Optional[str]:
        """Map nutrient name to schema field name."""
        return self.NUTRIENT_MAPPINGS.get(nutrient_name)
    
    def _build_nutrient_totals(self, totals: Dict[str, float]) -> NutrientTotals:
        """Build NutrientTotals object from totals dict."""
        # Separate known nutrients from others
        known_totals = {}
        other_nutrients = {}
        
        for key, value in totals.items():
            if key.startswith("other_"):
                other_nutrients[key[6:]] = value
            else:
                known_totals[key] = value
        
        # Calculate calories from macros if Energy is missing or incomplete
        # Use the 4-4-9 rule: protein(4 kcal/g), carbs(4 kcal/g), fat(9 kcal/g)
        protein = known_totals.get("protein_g", 0)
        carbs = known_totals.get("carbohydrates_g", 0)
        fat = known_totals.get("fat_g", 0)
        macros_calories = (protein * 4) + (carbs * 4) + (fat * 9)
        
        # If we have macros but calories is missing or very incomplete, use macro-calculated calories
        calories_from_db = known_totals.get("calories", 0) or 0
        
        # If DB calories is less than 50% of macro-calculated calories, use macro calculation
        if macros_calories > 0 and calories_from_db < (macros_calories * 0.5):
            logger.info(
                f"Using macro-calculated calories ({macros_calories:.1f}) instead of "
                f"incomplete DB calories ({calories_from_db:.1f})"
            )
            known_totals["calories"] = macros_calories
        
        return NutrientTotals(
            **known_totals,
            other_nutrients=other_nutrients
        )
