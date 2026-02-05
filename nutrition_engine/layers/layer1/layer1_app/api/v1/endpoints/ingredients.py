"""Ingredient search and lookup endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from layer1_app.core.logging import logger
from layer1_app.core.security import verify_api_key
from layer1_app.db.session import get_db
from layer1_app.db.models import Ingredient, IngredientSynonym, USDAFood, FoodNutrient, Nutrient
from layer1_app.schemas.recipe import IngredientSearchResponse, IngredientSearchResult
from layer1_app.schemas.nutrient import NutrientValue

router = APIRouter()


@router.get("/search", response_model=IngredientSearchResponse)
async def search_ingredients(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Search for ingredients by name or synonym.
    
    Returns matching ingredients with their canonical names,
    categories, and synonym mappings.
    """
    try:
        search_term = f"%{q.lower()}%"
        
        # Search in ingredient names
        ingredient_matches = db.query(Ingredient).filter(
            Ingredient.name.ilike(search_term)
        ).limit(limit).all()
        
        # Search in synonyms
        synonym_matches = db.query(Ingredient).join(
            IngredientSynonym
        ).filter(
            IngredientSynonym.synonym.ilike(search_term)
        ).limit(limit).all()
        
        # Combine and deduplicate
        all_matches = {ing.id: ing for ing in ingredient_matches + synonym_matches}
        ingredients = list(all_matches.values())[:limit]
        
        # Build results
        results = []
        for ingredient in ingredients:
            # Get synonyms
            synonyms = [syn.synonym for syn in ingredient.synonyms]
            
            # Count USDA foods
            usda_count = db.query(func.count(USDAFood.fdc_id)).filter(
                USDAFood.ingredient_id == ingredient.id
            ).scalar()
            
            results.append(IngredientSearchResult(
                ingredient_id=ingredient.id,
                name=ingredient.name,
                category=ingredient.category,
                synonyms=synonyms,
                usda_foods_count=usda_count or 0
            ))
        
        logger.info(f"Ingredient search: '{q}' returned {len(results)} results")
        
        return IngredientSearchResponse(
            query=q,
            results=results,
            total=len(results)
        )
    
    except Exception as e:
        logger.error(f"Error searching ingredients: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching ingredients: {str(e)}"
        )

@router.get("/{ingredient_id}/nutrients", response_model=List[NutrientValue])
async def get_ingredient_nutrients(
    ingredient_id: int,
    cooking_state: Optional[str] = Query(None, description="Cooking state (raw, cooked, baked, etc.)"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get nutrient profile for a specific ingredient.
    
    Returns nutrient values per 100g for the ingredient.
    Optionally filter by cooking state.
    """
    try:
        # Get ingredient
        ingredient = db.query(Ingredient).filter(
            Ingredient.id == ingredient_id
        ).first()
        
        if not ingredient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingredient {ingredient_id} not found"
            )
        
        # Get USDA food for this ingredient
        query = db.query(USDAFood).filter(
            USDAFood.ingredient_id == ingredient_id
        )
        
        if cooking_state:
            query = query.filter(
                USDAFood.cooking_state.ilike(f"%{cooking_state}%")
            )
        
        usda_food = query.first()
        
        if not usda_food:
            logger.warning(
                f"No USDA food found for ingredient {ingredient_id} "
                f"(cooking_state: {cooking_state})"
            )
            return []
        
        # Get nutrients for this food
        food_nutrients = db.query(FoodNutrient, Nutrient).join(
            Nutrient
        ).filter(
            FoodNutrient.fdc_id == usda_food.fdc_id
        ).all()
        
        results = []
        for fn, nutrient in food_nutrients:
            results.append(NutrientValue(
                nutrient_id=nutrient.id,
                nutrient_name=nutrient.name,
                amount_per_100g=fn.amount_per_100g,
                unit=nutrient.unit
            ))
        
        logger.info(
            f"Retrieved {len(results)} nutrients for ingredient {ingredient_id} "
            f"(FDC ID: {usda_food.fdc_id})"
        )
        
        return results
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ingredient nutrients: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting ingredient nutrients: {str(e)}"
        )
