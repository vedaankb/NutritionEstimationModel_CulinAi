"""API v1 package."""

from fastapi import APIRouter

from layer1_app.api.v1.endpoints import recipe, ingredients

api_router = APIRouter()

api_router.include_router(recipe.router, prefix="/recipe", tags=["Recipe"])
api_router.include_router(ingredients.router, prefix="/ingredients", tags=["Ingredients"])
