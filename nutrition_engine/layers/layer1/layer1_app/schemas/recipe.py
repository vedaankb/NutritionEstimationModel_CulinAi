"""Recipe analysis request and response schemas."""

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class RecipeIngredient(BaseModel):
    """Single ingredient in a recipe."""
    
    text: str = Field(..., description="Raw ingredient text (e.g., '2 cups flour')")
    
    model_config = ConfigDict(from_attributes=True)


class RecipeRequest(BaseModel):
    """Request schema for recipe analysis."""
    
    ingredients: List[str] = Field(
        ..., 
        min_length=1,
        description="List of ingredient strings",
        examples=[["2 cups flour", "3 eggs", "1 tbsp butter"]]
    )
    cooking_method: Optional[str] = Field(
        None,
        description="Cooking method (e.g., 'baked', 'boiled', 'fried', 'raw')",
        examples=["baked"]
    )
    cooking_time_minutes: Optional[int] = Field(
        None,
        ge=0,
        description="Cooking time in minutes"
    )
    servings: Optional[int] = Field(
        1,
        ge=1,
        description="Number of servings"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ingredients": [
                    "2 cups all-purpose flour",
                    "3 large eggs",
                    "1 tbsp butter"
                ],
                "cooking_method": "baked",
                "cooking_time_minutes": 25,
                "servings": 4
            }
        }
    )


class ParsedIngredient(BaseModel):
    """Parsed ingredient with extracted components."""
    
    original_text: str
    quantity: float
    unit: str
    ingredient_name: str
    ingredient_id: Optional[int]
    mass_g: float
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


class NutrientContribution(BaseModel):
    """Individual ingredient contribution to a nutrient."""
    
    ingredient_name: str
    mass_g: float
    nutrient_name: str
    nutrient_unit: str
    raw_contribution: float
    retention_factor: float
    final_contribution: float
    source_fdc_id: Optional[int] = None


class ValidationResult(BaseModel):
    """Validation results for nutrient calculations."""
    
    calorie_check_passed: bool
    calorie_delta_percent: Optional[float] = None
    calculated_calories: Optional[float] = None
    macros_calories: Optional[float] = None
    mass_check_passed: bool = True
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class NutrientTotals(BaseModel):
    """Total nutrients for a recipe."""
    
    # Macronutrients
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbohydrates_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    
    # Micronutrients (vitamins)
    vitamin_a_mcg: Optional[float] = None
    vitamin_c_mg: Optional[float] = None
    vitamin_d_mcg: Optional[float] = None
    vitamin_e_mg: Optional[float] = None
    vitamin_k_mcg: Optional[float] = None
    thiamin_mg: Optional[float] = None
    riboflavin_mg: Optional[float] = None
    niacin_mg: Optional[float] = None
    vitamin_b6_mg: Optional[float] = None
    folate_mcg: Optional[float] = None
    vitamin_b12_mcg: Optional[float] = None
    
    # Micronutrients (minerals)
    calcium_mg: Optional[float] = None
    iron_mg: Optional[float] = None
    magnesium_mg: Optional[float] = None
    phosphorus_mg: Optional[float] = None
    potassium_mg: Optional[float] = None
    sodium_mg: Optional[float] = None
    zinc_mg: Optional[float] = None
    
    # Additional fields for any other nutrients
    other_nutrients: Dict[str, float] = Field(default_factory=dict)


class RecipeAnalysisResponse(BaseModel):
    """Response schema for recipe analysis."""
    
    totals: NutrientTotals
    per_serving: Optional[NutrientTotals] = None
    parsed_ingredients: List[ParsedIngredient]
    audit_trail: List[NutrientContribution]
    validation: ValidationResult
    cooking_method: Optional[str] = None
    total_mass_g: float
    servings: int = 1
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "totals": {
                    "calories": 850,
                    "protein_g": 24.5,
                    "carbohydrates_g": 95.2,
                    "fat_g": 12.3,
                    "fiber_g": 3.2
                },
                "per_serving": {
                    "calories": 212.5,
                    "protein_g": 6.125,
                    "carbohydrates_g": 23.8,
                    "fat_g": 3.075,
                    "fiber_g": 0.8
                },
                "parsed_ingredients": [
                    {
                        "original_text": "2 cups all-purpose flour",
                        "quantity": 2.0,
                        "unit": "cup",
                        "ingredient_name": "all-purpose flour",
                        "ingredient_id": 123,
                        "mass_g": 240.0,
                        "confidence": 0.95,
                        "warnings": []
                    }
                ],
                "audit_trail": [],
                "validation": {
                    "calorie_check_passed": True,
                    "calorie_delta_percent": 2.3,
                    "warnings": [],
                    "errors": []
                },
                "cooking_method": "baked",
                "total_mass_g": 350.0,
                "servings": 4
            }
        }
    )


class IngredientSearchResult(BaseModel):
    """Result for ingredient search."""
    
    ingredient_id: int
    name: str
    category: Optional[str] = None
    synonyms: List[str] = Field(default_factory=list)
    usda_foods_count: int = 0


class IngredientSearchResponse(BaseModel):
    """Response schema for ingredient search."""
    
    query: str
    results: List[IngredientSearchResult]
    total: int
    
    model_config = ConfigDict(from_attributes=True)
