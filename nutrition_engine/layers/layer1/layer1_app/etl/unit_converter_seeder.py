"""Seed unit conversion data for common ingredients."""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from layer1_app.core.logging import logger
from layer1_app.db.session import SessionLocal
from layer1_app.db.models import Ingredient, UnitConversion


class UnitConversionSeeder:
    """Seed unit conversion data."""
    
    # Common unit conversions
    # Format: {ingredient_name: [(unit, grams, description), ...]}
    CONVERSIONS = {
        "all-purpose flour": [
            ("cup", 120, "1 cup all-purpose flour"),
            ("tablespoon", 7.5, "1 tablespoon flour"),
            ("teaspoon", 2.5, "1 teaspoon flour"),
        ],
        "sugar": [
            ("cup", 200, "1 cup granulated sugar"),
            ("tablespoon", 12.5, "1 tablespoon sugar"),
            ("teaspoon", 4.2, "1 teaspoon sugar"),
        ],
        "butter": [
            ("cup", 227, "1 cup butter (2 sticks)"),
            ("tablespoon", 14.2, "1 tablespoon butter"),
            ("teaspoon", 4.7, "1 teaspoon butter"),
            ("stick", 113.5, "1 stick butter"),
        ],
        "milk": [
            ("cup", 244, "1 cup milk"),
            ("tablespoon", 15, "1 tablespoon milk"),
            ("teaspoon", 5, "1 teaspoon milk"),
        ],
        "egg": [
            ("large", 50, "1 large egg"),
            ("medium", 44, "1 medium egg"),
            ("small", 38, "1 small egg"),
            ("piece", 50, "1 egg (assume large)"),
        ],
        "chicken breast": [
            ("piece", 174, "1 medium chicken breast"),
            ("large", 250, "1 large chicken breast"),
            ("small", 120, "1 small chicken breast"),
        ],
        "onion": [
            ("medium", 110, "1 medium onion"),
            ("large", 150, "1 large onion"),
            ("small", 70, "1 small onion"),
            ("cup", 160, "1 cup chopped onion"),
        ],
        "garlic": [
            ("clove", 3, "1 clove garlic"),
            ("teaspoon", 2.8, "1 teaspoon minced garlic"),
        ],
        "olive oil": [
            ("cup", 216, "1 cup olive oil"),
            ("tablespoon", 13.5, "1 tablespoon olive oil"),
            ("teaspoon", 4.5, "1 teaspoon olive oil"),
        ],
        "rice": [
            ("cup", 185, "1 cup uncooked rice"),
            ("tablespoon", 11.6, "1 tablespoon rice"),
        ],
        "pasta": [
            ("cup", 100, "1 cup uncooked pasta"),
            ("piece", 2, "1 piece pasta"),
        ],
        "tomato": [
            ("medium", 123, "1 medium tomato"),
            ("large", 182, "1 large tomato"),
            ("small", 91, "1 small tomato"),
            ("cup", 180, "1 cup chopped tomato"),
        ],
        "potato": [
            ("medium", 173, "1 medium potato"),
            ("large", 300, "1 large potato"),
            ("small", 138, "1 small potato"),
            ("cup", 150, "1 cup diced potato"),
        ],
        "carrot": [
            ("medium", 61, "1 medium carrot"),
            ("large", 72, "1 large carrot"),
            ("cup", 128, "1 cup chopped carrot"),
        ],
        "apple": [
            ("medium", 182, "1 medium apple"),
            ("large", 223, "1 large apple"),
            ("small", 149, "1 small apple"),
            ("cup", 125, "1 cup sliced apple"),
        ],
        "banana": [
            ("medium", 118, "1 medium banana"),
            ("large", 136, "1 large banana"),
            ("small", 101, "1 small banana"),
        ],
        "bread": [
            ("slice", 28, "1 slice bread"),
            ("piece", 28, "1 piece bread"),
        ],
        "cheese": [
            ("cup", 113, "1 cup shredded cheese"),
            ("slice", 28, "1 slice cheese"),
            ("tablespoon", 7, "1 tablespoon grated cheese"),
        ],
        "yogurt": [
            ("cup", 245, "1 cup yogurt"),
            ("tablespoon", 15, "1 tablespoon yogurt"),
        ],
        "honey": [
            ("cup", 340, "1 cup honey"),
            ("tablespoon", 21, "1 tablespoon honey"),
            ("teaspoon", 7, "1 teaspoon honey"),
        ],
        "salt": [
            ("tablespoon", 18, "1 tablespoon salt"),
            ("teaspoon", 6, "1 teaspoon salt"),
            ("pinch", 0.5, "1 pinch salt"),
        ],
        "pepper": [
            ("tablespoon", 6.9, "1 tablespoon pepper"),
            ("teaspoon", 2.3, "1 teaspoon pepper"),
            ("pinch", 0.3, "1 pinch pepper"),
        ],
    }
    
    def __init__(self, db: Session):
        """Initialize seeder with database session."""
        self.db = db
    
    def seed_conversions(self) -> None:
        """Seed unit conversions into database."""
        logger.info("Seeding unit conversions...")
        
        # Get all ingredients
        ingredients = {ing.name.lower(): ing for ing in self.db.query(Ingredient).all()}
        
        conversions = []
        
        for ingredient_name, units in self.CONVERSIONS.items():
            # Try to find ingredient (case-insensitive, partial match)
            ingredient = None
            
            for db_name, db_ingredient in ingredients.items():
                if ingredient_name in db_name or db_name in ingredient_name:
                    ingredient = db_ingredient
                    break
            
            if not ingredient:
                logger.warning(f"Ingredient '{ingredient_name}' not found, creating it")
                # Create ingredient
                ingredient = Ingredient(
                    name=ingredient_name,
                    category="common",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(ingredient)
                self.db.commit()
                self.db.refresh(ingredient)
            
            for unit, grams, description in units:
                conversions.append({
                    "ingredient_id": ingredient.id,
                    "unit": unit,
                    "grams": grams,
                    "description": description,
                    "created_at": datetime.utcnow()
                })
        
        # Batch upsert
        if conversions:
            self._batch_upsert(conversions)
            logger.info(f"Seeded {len(conversions)} unit conversions")
        else:
            logger.warning("No unit conversions to seed")
    
    def _batch_upsert(self, data: List[dict]) -> None:
        """Batch upsert unit conversions."""
        batch_size = 100
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            
            for conversion in batch:
                # Check if exists
                existing = self.db.query(UnitConversion).filter(
                    UnitConversion.ingredient_id == conversion["ingredient_id"],
                    UnitConversion.unit == conversion["unit"]
                ).first()
                
                if existing:
                    existing.grams = conversion["grams"]
                    existing.description = conversion["description"]
                else:
                    self.db.add(UnitConversion(**conversion))
            
            self.db.commit()


def main():
    """Main entry point for CLI."""
    db = SessionLocal()
    
    try:
        seeder = UnitConversionSeeder(db)
        seeder.seed_conversions()
        logger.info("Unit conversions seeded successfully")
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
