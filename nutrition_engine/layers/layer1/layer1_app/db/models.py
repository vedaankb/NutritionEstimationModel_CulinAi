"""SQLAlchemy database models."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, 
    DateTime, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from layer1_app.db.session import Base


class Ingredient(Base):
    """Canonical ingredient with density information."""
    
    __tablename__ = "ingredients"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    density_g_per_ml: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    synonyms: Mapped[List["IngredientSynonym"]] = relationship(
        "IngredientSynonym", back_populates="ingredient", cascade="all, delete-orphan"
    )
    usda_foods: Mapped[List["USDAFood"]] = relationship(
        "USDAFood", back_populates="ingredient"
    )
    
    def __repr__(self) -> str:
        return f"<Ingredient(id={self.id}, name='{self.name}')>"


class IngredientSynonym(Base):
    """Synonyms and alternate names for ingredients."""
    
    __tablename__ = "ingredient_synonyms"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False
    )
    synonym: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="synonyms")
    
    __table_args__ = (
        UniqueConstraint("ingredient_id", "synonym", name="uix_ingredient_synonym"),
        Index("idx_synonym_search", "synonym"),
    )
    
    def __repr__(self) -> str:
        return f"<IngredientSynonym(synonym='{self.synonym}', confidence={self.confidence})>"


class USDAFood(Base):
    """USDA FoodData Central food entries."""
    
    __tablename__ = "usda_foods"
    
    fdc_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    cooking_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    ingredient_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ingredients.id"), nullable=True, index=True
    )
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ingredient: Mapped[Optional["Ingredient"]] = relationship(
        "Ingredient", back_populates="usda_foods"
    )
    nutrients: Mapped[List["FoodNutrient"]] = relationship(
        "FoodNutrient", back_populates="food", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_food_description", "description"),
        Index("idx_food_cooking_state", "cooking_state"),
    )
    
    def __repr__(self) -> str:
        return f"<USDAFood(fdc_id={self.fdc_id}, description='{self.description[:50]}...')>"


class Nutrient(Base):
    """Nutrient definitions (vitamins, minerals, macros)."""
    
    __tablename__ = "nutrients"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    nutrient_number: Mapped[Optional[str]] = mapped_column(String(10), unique=True, index=True)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    food_nutrients: Mapped[List["FoodNutrient"]] = relationship(
        "FoodNutrient", back_populates="nutrient"
    )
    retention_factors: Mapped[List["RetentionFactor"]] = relationship(
        "RetentionFactor", back_populates="nutrient"
    )
    
    def __repr__(self) -> str:
        return f"<Nutrient(id={self.id}, name='{self.name}', unit='{self.unit}')>"


class FoodNutrient(Base):
    """Nutrient values for specific foods (per 100g)."""
    
    __tablename__ = "food_nutrients"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fdc_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usda_foods.fdc_id", ondelete="CASCADE"), nullable=False
    )
    nutrient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("nutrients.id", ondelete="CASCADE"), nullable=False
    )
    amount_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    data_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    food: Mapped["USDAFood"] = relationship("USDAFood", back_populates="nutrients")
    nutrient: Mapped["Nutrient"] = relationship("Nutrient", back_populates="food_nutrients")
    
    __table_args__ = (
        UniqueConstraint("fdc_id", "nutrient_id", name="uix_food_nutrient"),
        Index("idx_food_nutrients_lookup", "fdc_id", "nutrient_id"),
    )
    
    def __repr__(self) -> str:
        return f"<FoodNutrient(fdc_id={self.fdc_id}, nutrient_id={self.nutrient_id}, amount={self.amount_per_100g})>"


class CookingMethod(Base):
    """Cooking methods for retention factor application."""
    
    __tablename__ = "cooking_methods"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    retention_factors: Mapped[List["RetentionFactor"]] = relationship(
        "RetentionFactor", back_populates="cooking_method"
    )
    
    def __repr__(self) -> str:
        return f"<CookingMethod(id={self.id}, name='{self.name}')>"


class RetentionFactor(Base):
    """Nutrient retention factors by cooking method."""
    
    __tablename__ = "retention_factors"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nutrient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("nutrients.id", ondelete="CASCADE"), nullable=False
    )
    cooking_method_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cooking_methods.id", ondelete="CASCADE"), nullable=False
    )
    retention_factor: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    nutrient: Mapped["Nutrient"] = relationship("Nutrient", back_populates="retention_factors")
    cooking_method: Mapped["CookingMethod"] = relationship(
        "CookingMethod", back_populates="retention_factors"
    )
    
    __table_args__ = (
        UniqueConstraint("nutrient_id", "cooking_method_id", name="uix_nutrient_cooking_method"),
        Index("idx_retention_lookup", "nutrient_id", "cooking_method_id"),
    )
    
    def __repr__(self) -> str:
        return f"<RetentionFactor(nutrient_id={self.nutrient_id}, method_id={self.cooking_method_id}, factor={self.retention_factor})>"


class APIKey(Base):
    """API keys for authentication."""
    
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<APIKey(name='{self.name}', active={self.is_active})>"


class UnitConversion(Base):
    """Unit conversions and density lookups for common ingredients."""
    
    __tablename__ = "unit_conversions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ingredients.id"), nullable=True, index=True
    )
    unit: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    grams: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ingredient: Mapped[Optional["Ingredient"]] = relationship("Ingredient")
    
    __table_args__ = (
        Index("idx_unit_conversion_lookup", "ingredient_id", "unit"),
    )
    
    def __repr__(self) -> str:
        return f"<UnitConversion(unit='{self.unit}', grams={self.grams})>"
