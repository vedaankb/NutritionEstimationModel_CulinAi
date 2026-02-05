"""Load USDA retention factors into database."""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from layer1_app.core.logging import logger
from layer1_app.db.session import SessionLocal
from layer1_app.db.models import Nutrient, CookingMethod, RetentionFactor


class RetentionFactorLoader:
    """Load nutrient retention factors from USDA data."""
    
    # USDA Retention Factors - simplified version
    # Source: USDA Table of Nutrient Retention Factors, Release 6
    # Format: {nutrient_name: {cooking_method: retention_factor}}
    RETENTION_FACTORS = {
        # Vitamins - water-soluble (more sensitive to cooking)
        "Vitamin C, total ascorbic acid": {
            "raw": 1.0,
            "baked": 0.75,
            "boiled": 0.55,
            "fried": 0.70,
            "grilled": 0.80,
            "roasted": 0.75,
            "steamed": 0.85,
            "microwaved": 0.90,
        },
        "Thiamin": {
            "raw": 1.0,
            "baked": 0.85,
            "boiled": 0.70,
            "fried": 0.80,
            "grilled": 0.85,
            "roasted": 0.85,
            "steamed": 0.90,
            "microwaved": 0.90,
        },
        "Riboflavin": {
            "raw": 1.0,
            "baked": 0.90,
            "boiled": 0.75,
            "fried": 0.85,
            "grilled": 0.90,
            "roasted": 0.90,
            "steamed": 0.95,
            "microwaved": 0.95,
        },
        "Niacin": {
            "raw": 1.0,
            "baked": 0.90,
            "boiled": 0.75,
            "fried": 0.85,
            "grilled": 0.90,
            "roasted": 0.90,
            "steamed": 0.95,
            "microwaved": 0.95,
        },
        "Vitamin B-6": {
            "raw": 1.0,
            "baked": 0.85,
            "boiled": 0.70,
            "fried": 0.80,
            "grilled": 0.85,
            "roasted": 0.85,
            "steamed": 0.90,
            "microwaved": 0.90,
        },
        "Folate, total": {
            "raw": 1.0,
            "baked": 0.80,
            "boiled": 0.60,
            "fried": 0.75,
            "grilled": 0.85,
            "roasted": 0.80,
            "steamed": 0.90,
            "microwaved": 0.90,
        },
        "Vitamin B-12": {
            "raw": 1.0,
            "baked": 0.90,
            "boiled": 0.80,
            "fried": 0.85,
            "grilled": 0.90,
            "roasted": 0.90,
            "steamed": 0.95,
            "microwaved": 0.95,
        },
        # Vitamins - fat-soluble (more stable)
        "Vitamin A, RAE": {
            "raw": 1.0,
            "baked": 0.90,
            "boiled": 0.85,
            "fried": 0.90,
            "grilled": 0.90,
            "roasted": 0.90,
            "steamed": 0.95,
            "microwaved": 0.95,
        },
        "Vitamin D (D2 + D3)": {
            "raw": 1.0,
            "baked": 0.95,
            "boiled": 0.90,
            "fried": 0.95,
            "grilled": 0.95,
            "roasted": 0.95,
            "steamed": 0.95,
            "microwaved": 0.95,
        },
        "Vitamin E (alpha-tocopherol)": {
            "raw": 1.0,
            "baked": 0.85,
            "boiled": 0.80,
            "fried": 0.75,  # Oxidation from frying
            "grilled": 0.85,
            "roasted": 0.85,
            "steamed": 0.95,
            "microwaved": 0.95,
        },
        "Vitamin K (phylloquinone)": {
            "raw": 1.0,
            "baked": 0.90,
            "boiled": 0.85,
            "fried": 0.90,
            "grilled": 0.90,
            "roasted": 0.90,
            "steamed": 0.95,
            "microwaved": 0.95,
        },
        # Minerals - relatively stable
        "Calcium, Ca": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 0.95,  # Some loss to cooking water
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 1.0,
            "microwaved": 1.0,
        },
        "Iron, Fe": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 0.95,
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 1.0,
            "microwaved": 1.0,
        },
        "Magnesium, Mg": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 0.90,
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 0.95,
            "microwaved": 1.0,
        },
        "Phosphorus, P": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 0.95,
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 1.0,
            "microwaved": 1.0,
        },
        "Potassium, K": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 0.85,  # Leaches into water
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 0.95,
            "microwaved": 1.0,
        },
        "Sodium, Na": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 0.90,
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 0.95,
            "microwaved": 1.0,
        },
        "Zinc, Zn": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 0.95,
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 1.0,
            "microwaved": 1.0,
        },
        # Macronutrients - very stable
        "Energy": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 1.0,
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 1.0,
            "microwaved": 1.0,
        },
        "Protein": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 1.0,
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 1.0,
            "microwaved": 1.0,
        },
        "Carbohydrate, by difference": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 1.0,
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 1.0,
            "microwaved": 1.0,
        },
        "Total lipid (fat)": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 1.0,
            "fried": 1.0,
            "grilled": 0.95,  # Some dripping
            "roasted": 0.95,
            "steamed": 1.0,
            "microwaved": 1.0,
        },
        "Fiber, total dietary": {
            "raw": 1.0,
            "baked": 1.0,
            "boiled": 1.0,
            "fried": 1.0,
            "grilled": 1.0,
            "roasted": 1.0,
            "steamed": 1.0,
            "microwaved": 1.0,
        },
    }
    
    def __init__(self, db: Session):
        """Initialize loader with database session."""
        self.db = db
    
    def load_retention_factors(self) -> None:
        """Load retention factors into database."""
        logger.info("Loading retention factors...")
        
        # Get all nutrients and cooking methods
        nutrients = {n.name: n for n in self.db.query(Nutrient).all()}
        cooking_methods = {m.name: m for m in self.db.query(CookingMethod).all()}
        
        retention_factors = []
        
        for nutrient_name, methods in self.RETENTION_FACTORS.items():
            if nutrient_name not in nutrients:
                logger.warning(f"Nutrient '{nutrient_name}' not found in database")
                continue
            
            nutrient = nutrients[nutrient_name]
            
            for method_name, factor in methods.items():
                if method_name not in cooking_methods:
                    logger.warning(f"Cooking method '{method_name}' not found in database")
                    continue
                
                cooking_method = cooking_methods[method_name]
                
                retention_factors.append({
                    "nutrient_id": nutrient.id,
                    "cooking_method_id": cooking_method.id,
                    "retention_factor": factor,
                    "source": "USDA Table of Nutrient Retention Factors, Release 6",
                    "created_at": datetime.utcnow()
                })
        
        # Batch upsert
        if retention_factors:
            self._batch_upsert(retention_factors)
            logger.info(f"Loaded {len(retention_factors)} retention factors")
        else:
            logger.warning("No retention factors to load")
    
    def _batch_upsert(self, data: List[dict]) -> None:
        """Batch upsert retention factors."""
        batch_size = 100
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            
            stmt = insert(RetentionFactor).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["nutrient_id", "cooking_method_id"],
                set_={
                    "retention_factor": stmt.excluded.retention_factor,
                    "source": stmt.excluded.source,
                }
            )
            
            self.db.execute(stmt)
            self.db.commit()


def main():
    """Main entry point for CLI."""
    db = SessionLocal()
    
    try:
        loader = RetentionFactorLoader(db)
        loader.load_retention_factors()
        logger.info("Retention factors loaded successfully")
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
