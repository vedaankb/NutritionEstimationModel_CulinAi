"""Nutrient-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class NutrientBase(BaseModel):
    """Base nutrient schema."""
    
    name: str = Field(..., min_length=1, max_length=255)
    unit: str = Field(..., min_length=1, max_length=20)
    nutrient_number: Optional[str] = Field(None, max_length=10)
    rank: Optional[int] = None


class NutrientCreate(NutrientBase):
    """Schema for creating a nutrient."""
    pass


class NutrientUpdate(BaseModel):
    """Schema for updating a nutrient."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    nutrient_number: Optional[str] = Field(None, max_length=10)
    rank: Optional[int] = None


class Nutrient(NutrientBase):
    """Schema for nutrient response."""
    
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class NutrientValue(BaseModel):
    """Schema for nutrient value in a food."""
    
    nutrient_id: int
    nutrient_name: str
    amount_per_100g: float
    unit: str
    
    model_config = ConfigDict(from_attributes=True)


class NutrientTotal(BaseModel):
    """Schema for total nutrient amount in a recipe."""
    
    nutrient_name: str
    amount: float
    unit: str
    
    model_config = ConfigDict(from_attributes=True)
