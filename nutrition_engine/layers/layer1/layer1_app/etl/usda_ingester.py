import argparse
import os
import sys
import zipfile
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import pandas as pd
import httpx
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from layer1_app.core.config import get_settings
from layer1_app.core.logging import logger
from layer1_app.db.session import SessionLocal, engine, Base
from layer1_app.db.models import (
    Ingredient, USDAFood, Nutrient, FoodNutrient,
    CookingMethod, RetentionFactor, UnitConversion
)

settings = get_settings()


class USDAIngester:    
    FOUNDATION_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2025-12-18.zip"    
    DATA_DIR = Path("/app/data/usda/foundation")
    
    BATCH_SIZE = 1000
    
    IMPORTANT_NUTRIENTS = {
        "1008": "Energy",
        "1003": "Protein",
        "1005": "Carbohydrate, by difference",
        "1004": "Total lipid (fat)",
        "1079": "Fiber, total dietary",
        "2000": "Sugars, total including NLEA",
        "1106": "Vitamin A, RAE",
        "1162": "Vitamin C, total ascorbic acid",
        "1114": "Vitamin D (D2 + D3)",
        "1109": "Vitamin E (alpha-tocopherol)",
        "1185": "Vitamin K (phylloquinone)",
        "1165": "Thiamin",
        "1166": "Riboflavin",
        "1167": "Niacin",
        "1175": "Vitamin B-6",
        "1177": "Folate, total",
        "1178": "Vitamin B-12",
        "1087": "Calcium, Ca",
        "1089": "Iron, Fe",
        "1090": "Magnesium, Mg",
        "1091": "Phosphorus, P",
        "1092": "Potassium, K",
        "1093": "Sodium, Na",
        "1095": "Zinc, Zn",
    }
    
    def __init__(self, db: Session):
        """Initialize ingester with database session."""
        self.db = db
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def download_data(self, year: int = 2024) -> None:        
        logger.info("Downloading USDA FoodData Central data...")
        
        foundation_url = self.FOUNDATION_URL
        
        logger.info(f"Downloading Foundation Foods from {foundation_url}")
        self._download_file(foundation_url, self.DATA_DIR / "foundation.zip")
        
        # Extract
        logger.info("Extracting files...")
        with zipfile.ZipFile(self.DATA_DIR / "foundation.zip", 'r') as zip_ref:
            zip_ref.extractall(self.DATA_DIR)
        
        logger.info("Download and extraction complete")
    
    def _download_file(self, url: str, destination: Path) -> None:
        """Download a file from URL."""
        try:
            with httpx.stream("GET", url, timeout=300.0, follow_redirects=True) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                with open(destination, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size:
                            progress = (downloaded / total_size) * 100
                            print(f"\rProgress: {progress:.1f}%", end="", flush=True)
                
                print()  # New line after progress
                logger.info(f"Downloaded {destination.name}")
        
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            raise
    
    def ingest_data(self) -> None:
        """Ingest all USDA data into database."""
        logger.info("Starting USDA data ingestion...")
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
        # Ingest in order due to foreign key dependencies
        self._ingest_nutrients()
        self._ingest_foods()
        self._ingest_food_nutrients()
        self._seed_cooking_methods()
        self._seed_ingredients()
        
        logger.info("USDA data ingestion complete")
    
    def _ingest_nutrients(self) -> None:        
        logger.info("Ingesting nutrients...")
                
        nutrient_file = self._find_file("nutrient.csv")
        if not nutrient_file:
            logger.error("nutrient.csv not found")
            return
        
        df = pd.read_csv(nutrient_file)
        
        # Filter to important nutrients
        df = df[df['id'].astype(str).isin(self.IMPORTANT_NUTRIENTS.keys())]
        
        logger.info(f"Found {len(df)} important nutrients")
        
        # Prepare data
        nutrients = []
        for _, row in df.iterrows():
            nutrients.append({
                "id": int(row["id"]),
                "name": row["name"],
                "unit": row["unit_name"],
                "nutrient_number": str(row["id"]), 
                "rank": int(row.get("rank", 0)) if pd.notna(row.get("rank")) else None,
                "created_at": datetime.utcnow()
            })
        
        self._batch_upsert(Nutrient, nutrients, ["nutrient_number"])
        
        logger.info(f"Ingested {len(nutrients)} nutrients")
    
    def _ingest_foods(self) -> None:
        """Ingest food entries."""
        logger.info("Ingesting foods...")
        
        # Find food file
        food_file = self._find_file("food.csv")
        if not food_file:
            logger.error("food.csv not found")
            return
        
        # Read foods
        df = pd.read_csv(food_file)
        
        # Filter to Foundation and SR Legacy foods
        df = df[df["data_type"].isin(["foundation_food", "sr_legacy_food"])]
        
        logger.info(f"Found {len(df)} foods")
        
        # Prepare data
        foods = []
        for _, row in df.iterrows():
            # Detect cooking state
            description = row["description"].lower()
            cooking_state = self._detect_cooking_state(description)
            
            foods.append({
                "fdc_id": int(row["fdc_id"]),
                "description": row["description"],
                "data_type": row["data_type"],
                "cooking_state": cooking_state,
                "publication_date": pd.to_datetime(row.get("publication_date")) if pd.notna(row.get("publication_date")) else None,
                "created_at": datetime.utcnow()
            })
        
        # Upsert in batches
        self._batch_upsert(USDAFood, foods, ["fdc_id"])
        
        logger.info(f"Ingested {len(foods)} foods")
    
    def _ingest_food_nutrients(self) -> None:
        """Ingest food-nutrient relationships."""
        logger.info("Ingesting food nutrients...")
        
        # Find food_nutrient file
        food_nutrient_file = self._find_file("food_nutrient.csv")
        if not food_nutrient_file:
            logger.error("food_nutrient.csv not found")
            return
        
        logger.info("Building nutrient ID mapping...")
        nutrients = self.db.query(Nutrient).all()
        nutrient_map = {
            int(n.nutrient_number): n.id 
            for n in nutrients 
            if n.nutrient_number
        }
        logger.info(f"Mapped {len(nutrient_map)} nutrients")
        
        # Build set of valid fdc_ids from usda_foods
        logger.info("Building valid fdc_id set...")
        valid_fdc_ids = set(
            row[0] for row in self.db.query(USDAFood.fdc_id).all()
        )
        logger.info(f"Found {len(valid_fdc_ids)} valid fdc_ids in usda_foods")
        
        chunk_size = 10000
        total_ingested = 0
        total_skipped = 0
        
        for chunk in pd.read_csv(food_nutrient_file, chunksize=chunk_size):
            chunk["nutrient_id"] = chunk["nutrient_id"].astype(int)
            chunk["fdc_id"] = chunk["fdc_id"].astype(int)
            
            # Filter by both nutrient_id AND fdc_id
            chunk = chunk[
                chunk["nutrient_id"].isin(nutrient_map.keys()) &
                chunk["fdc_id"].isin(valid_fdc_ids)
            ]
        
            food_nutrients = []
            for _, row in chunk.iterrows():
                if pd.notna(row.get("amount")):
                    usda_nutrient_id = int(row["nutrient_id"])
                    internal_nutrient_id = nutrient_map.get(usda_nutrient_id)
                    
                    if internal_nutrient_id is None:
                        total_skipped += 1
                        continue
                    
                    food_nutrients.append({
                        "fdc_id": int(row["fdc_id"]),
                        "nutrient_id": internal_nutrient_id,  
                        "amount_per_100g": float(row["amount"]),
                        "data_points": int(row.get("data_points", 0)) if pd.notna(row.get("data_points")) else None,
                        "min_value": float(row.get("min", 0)) if pd.notna(row.get("min")) else None,
                        "max_value": float(row.get("max", 0)) if pd.notna(row.get("max")) else None,
                    })
            
            if food_nutrients:
                # Note: We'll use id as auto-increment, so we don't include it
                self._batch_insert_ignore(FoodNutrient, food_nutrients)
                total_ingested += len(food_nutrients)
                logger.info(f"Ingested {total_ingested} food-nutrient relationships so far...")
        
        logger.info(f"Ingested total {total_ingested} food-nutrient relationships (skipped {total_skipped})")
    
    def _detect_cooking_state(self, description: str) -> Optional[str]:
        """Detect cooking state from food description."""
        description_lower = description.lower()
        
        cooking_states = {
            "raw": ["raw", "uncooked", "fresh"],
            "cooked": ["cooked", "boiled"],
            "baked": ["baked"],
            "fried": ["fried", "deep-fried", "pan-fried"],
            "grilled": ["grilled", "broiled"],
            "roasted": ["roasted"],
            "steamed": ["steamed"],
        }
        
        for state, keywords in cooking_states.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return state
        
        return None
    
    def _seed_cooking_methods(self) -> None:
        """Seed cooking methods."""
        logger.info("Seeding cooking methods...")
        
        methods = [
            {"name": "raw", "description": "No cooking applied"},
            {"name": "baked", "description": "Baked in an oven"},
            {"name": "boiled", "description": "Boiled in water"},
            {"name": "fried", "description": "Fried in oil or fat"},
            {"name": "grilled", "description": "Grilled or broiled"},
            {"name": "roasted", "description": "Roasted"},
            {"name": "steamed", "description": "Steamed"},
            {"name": "microwaved", "description": "Microwaved"},
        ]
        
        for method in methods:
            method["created_at"] = datetime.utcnow()
        
        self._batch_upsert(CookingMethod, methods, ["name"])
        
        logger.info(f"Seeded {len(methods)} cooking methods")
    
    def _seed_ingredients(self) -> None:
        """Seed common ingredients from USDA foods."""
        logger.info("Seeding ingredients from USDA foods...")
        
        # Get all USDA foods
        foods = self.db.query(USDAFood).limit(100).all()
        
        ingredients = []
        for food in foods:
            # Simplify description to create ingredient name
            name = self._simplify_food_name(food.description)
            
            if name and len(name) > 2:
                ingredients.append({
                    "name": name,
                    "category": self._guess_category(name),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
        
        # Remove duplicates
        unique_ingredients = {ing["name"]: ing for ing in ingredients}
        ingredients = list(unique_ingredients.values())
        
        if ingredients:
            self._batch_upsert(Ingredient, ingredients, ["name"])
            logger.info(f"Seeded {len(ingredients)} ingredients")
        
        # Link USDA foods to ingredients (simplified for now)
        # In production, this would use more sophisticated matching
        logger.info("Linking USDA foods to ingredients...")
        self._link_foods_to_ingredients()
    
    def _simplify_food_name(self, description: str) -> str:
        """Simplify USDA food description to ingredient name."""
        name = description.lower()
        
        # Remove cooking methods and descriptors
        remove_terms = [
            "raw", "cooked", "baked", "fried", "boiled", "grilled",
            "roasted", "steamed", "fresh", "frozen", "canned",
            "with", "without", "in", "of", ",", "  "
        ]
        
        for term in remove_terms:
            name = name.replace(term, " ")
        
        # Clean up
        name = " ".join(name.split())
        return name.strip()
    
    def _guess_category(self, name: str) -> str:
        """Guess ingredient category from name."""
        name_lower = name.lower()
        
        if any(word in name_lower for word in ["chicken", "beef", "pork", "fish", "meat", "turkey"]):
            return "protein"
        elif any(word in name_lower for word in ["flour", "rice", "bread", "pasta", "oat"]):
            return "grain"
        elif any(word in name_lower for word in ["milk", "cheese", "yogurt", "butter", "cream"]):
            return "dairy"
        elif any(word in name_lower for word in ["apple", "banana", "orange", "berry"]):
            return "fruit"
        elif any(word in name_lower for word in ["carrot", "broccoli", "spinach", "lettuce", "tomato"]):
            return "vegetable"
        else:
            return "other"
    
    def _link_foods_to_ingredients(self) -> None:
        """Link USDA foods to ingredients."""
        # Simple approach: match by name similarity
        ingredients = self.db.query(Ingredient).all()
        foods = self.db.query(USDAFood).filter(USDAFood.ingredient_id.is_(None)).limit(1000).all()
        
        updates = 0
        for food in foods:
            best_match = None
            best_score = 0.0
            
            food_desc_lower = food.description.lower()
            
            for ingredient in ingredients:
                if ingredient.name.lower() in food_desc_lower:
                    score = len(ingredient.name) / len(food_desc_lower)
                    if score > best_score:
                        best_score = score
                        best_match = ingredient
            
            if best_match and best_score > 0.1:
                food.ingredient_id = best_match.id
                updates += 1
        
        if updates > 0:
            self.db.commit()
            logger.info(f"Linked {updates} foods to ingredients")
    
    def _find_file(self, filename: str) -> Optional[Path]:
        """Find a file in the data directory."""
        for path in self.DATA_DIR.rglob(filename):
            return path
        return None
    
    def _batch_upsert(self, model, data: List[dict], conflict_columns: List[str]) -> None:
        """Batch upsert data into database."""
        if not data:
            return
        
        for i in range(0, len(data), self.BATCH_SIZE):
            batch = data[i:i + self.BATCH_SIZE]
            
            stmt = insert(model).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_={col: stmt.excluded[col] for col in batch[0].keys() if col not in conflict_columns}
            )
            
            self.db.execute(stmt)
            self.db.commit()
    
    def _batch_insert_ignore(self, model, data: List[dict]) -> None:
        """Batch insert data, ignoring conflicts."""
        if not data:
            return
        
        for i in range(0, len(data), self.BATCH_SIZE):
            batch = data[i:i + self.BATCH_SIZE]
            
            stmt = insert(model).values(batch)
            stmt = stmt.on_conflict_do_nothing()
            
            self.db.execute(stmt)
            self.db.commit()


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="USDA FoodData Central ingestion tool")
    parser.add_argument("--download", action="store_true", help="Download USDA data")
    parser.add_argument("--ingest", action="store_true", help="Ingest data into database")
    parser.add_argument("--year", type=int, default=2024, help="Year of data to download")
    
    args = parser.parse_args()
    
    if not args.download and not args.ingest:
        parser.print_help()
        return
    
    # Create database session
    db = SessionLocal()
    
    try:
        ingester = USDAIngester(db)
        
        if args.download:
            ingester.download_data(args.year)
        
        if args.ingest:
            ingester.ingest_data()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
