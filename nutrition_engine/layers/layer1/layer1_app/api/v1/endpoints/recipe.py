"""Recipe analysis endpoints."""

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from layer1_app.core.logging import logger
from layer1_app.core.security import verify_api_key
from layer1_app.db.session import get_db
from layer1_app.schemas.recipe import RecipeRequest, RecipeAnalysisResponse
from layer1_app.services.parser import IngredientParser
from layer1_app.services.calculator import NutrientCalculator
from layer1_app.services.validator import NutrientValidator

router = APIRouter()


@router.post("/analyze", response_model=RecipeAnalysisResponse)
async def analyze_recipe(
    recipe: RecipeRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyze a recipe and calculate nutrients.
    
    This endpoint takes a list of ingredient strings and a cooking method,
    then returns detailed nutritional information including:
    - Total nutrients (macros and micros)
    - Per-serving nutrients
    - Parsed ingredient details
    - Audit trail showing calculation steps
    - Validation results and warnings
    
    The calculation uses USDA FoodData Central nutrient densities and
    applies retention factors based on the cooking method.
    """
    start_time = time.time()
    
    try:
        # Initialize services
        parser = IngredientParser(db)
        calculator = NutrientCalculator(db)
        
        # Parse ingredients
        logger.info(f"Parsing {len(recipe.ingredients)} ingredients")
        parsed_ingredients = [parser.parse(ing) for ing in recipe.ingredients]
        
        # Check if any ingredients failed to parse
        failed_parses = [
            ing for ing in parsed_ingredients 
            if ing.ingredient_id is None
        ]
        
        if failed_parses and len(failed_parses) == len(parsed_ingredients):
            logger.error("All ingredients failed to parse")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not parse any ingredients. Please check ingredient names."
            )
        
        # Calculate nutrients
        logger.info(f"Calculating nutrients with cooking method: {recipe.cooking_method}")
        totals, audit_trail = calculator.calculate_recipe(
            parsed_ingredients,
            recipe.cooking_method
        )
        
        # Calculate total mass
        total_mass_g = sum(ing.mass_g for ing in parsed_ingredients)
        
        # Validate results
        validation = NutrientValidator.validate(
            totals,
            parsed_ingredients,
            total_mass_g
        )
        
        # Calculate per-serving if servings specified
        per_serving = None
        servings = recipe.servings or 1
        
        if servings > 1:
            per_serving_dict = {}
            for field, value in totals.model_dump().items():
                if value is not None and field != "other_nutrients":
                    per_serving_dict[field] = value / servings
                elif field == "other_nutrients":
                    per_serving_dict[field] = {
                        k: v / servings for k, v in value.items()
                    }
            
            from layer1_app.schemas.recipe import NutrientTotals
            per_serving = NutrientTotals(**per_serving_dict)
        
        # Log performance
        elapsed_time = time.time() - start_time
        logger.info(
            f"Recipe analyzed in {elapsed_time:.3f}s",
            extra={
                "ingredient_count": len(recipe.ingredients),
                "cooking_method": recipe.cooking_method,
                "total_calories": totals.calories,
                "validation_passed": validation.calorie_check_passed,
                "processing_time_s": elapsed_time
            }
        )
        
        return RecipeAnalysisResponse(
            totals=totals,
            per_serving=per_serving,
            parsed_ingredients=parsed_ingredients,
            audit_trail=audit_trail,
            validation=validation,
            cooking_method=recipe.cooking_method,
            total_mass_g=total_mass_g,
            servings=servings
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing recipe: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing recipe: {str(e)}"
        )
