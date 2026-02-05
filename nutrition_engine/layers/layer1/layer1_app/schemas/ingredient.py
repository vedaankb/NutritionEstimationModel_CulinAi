"""Ingredient-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class IngredientBase(BaseModel):
    """Base ingredient schema."""
    
    name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    density_g_per_ml: Optional[float] = Field(None, gt=0)


class IngredientCreate(IngredientBase):
    """Schema for creating an ingredient."""
    pass


class IngredientUpdate(BaseModel):
    """Schema for updating an ingredient."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    density_g_per_ml: Optional[float] = Field(None, gt=0)


class Ingredient(IngredientBase):
    """Schema for ingredient response."""
    
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class IngredientSynonymBase(BaseModel):
    """Base ingredient synonym schema."""
    
    synonym: str = Field(..., min_length=1, max_length=255)
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class IngredientSynonymCreate(IngredientSynonymBase):
    """Schema for creating an ingredient synonym."""
    
    ingredient_id: int


class IngredientSynonym(IngredientSynonymBase):
    """Schema for ingredient synonym response."""
    
    id: int
    ingredient_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class IngredientWithSynonyms(Ingredient):
    """Ingredient with its synonyms."""
    
    synonyms: List[IngredientSynonym] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


class UnitConversionBase(BaseModel):
    """Base unit conversion schema."""
    
    unit: str = Field(..., min_length=1, max_length=50)
    grams: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=255)


class UnitConversionCreate(UnitConversionBase):
    """Schema for creating a unit conversion."""
    
    ingredient_id: Optional[int] = None


class UnitConversion(UnitConversionBase):
    """Schema for unit conversion response."""
    
    id: int
    ingredient_id: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
