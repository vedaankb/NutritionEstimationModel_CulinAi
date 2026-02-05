"""NLP-based ingredient parser."""

import re
from fractions import Fraction
from typing import Optional, Tuple, List, Dict
from Levenshtein import distance as levenshtein_distance

import spacy
from sqlalchemy.orm import Session

from layer1_app.core.logging import logger
from layer1_app.db.models import Ingredient, IngredientSynonym, UnitConversion
from layer1_app.schemas.recipe import ParsedIngredient


try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")
    nlp = None


class IngredientParser:
    
    VOLUME_UNITS = {
        "cup": 237.0,
        "cups": 237.0,
        "c": 237.0,
        "tablespoon": 15.0,
        "tablespoons": 15.0,
        "tbsp": 15.0,
        "tbs": 15.0,
        "teaspoon": 5.0,
        "teaspoons": 5.0,
        "tsp": 5.0,
        "fluid ounce": 30.0,
        "fluid ounces": 30.0,
        "fl oz": 30.0,
        "fl. oz": 30.0,
        "pint": 473.0,
        "pints": 473.0,
        "quart": 946.0,
        "quarts": 946.0,
        "gallon": 3785.0,
        "gallons": 3785.0,
        "liter": 1000.0,
        "liters": 1000.0,
        "l": 1000.0,
        "milliliter": 1.0,
        "milliliters": 1.0,
        "ml": 1.0,
    }
    
    WEIGHT_UNITS = {
        "gram": 1.0,
        "grams": 1.0,
        "g": 1.0,
        "kilogram": 1000.0,
        "kilograms": 1000.0,
        "kg": 1000.0,
        "ounce": 28.35,
        "ounces": 28.35,
        "oz": 28.35,
        "pound": 453.59,
        "pounds": 453.59,
        "lb": 453.59,
        "lbs": 453.59,
        "milligram": 0.001,
        "milligrams": 0.001,
        "mg": 0.001,
    }
    
    # Piece/count units
    COUNT_UNITS = {
        "piece": "piece",
        "pieces": "piece",
        "whole": "piece",
        "item": "piece",
        "items": "piece",
        "clove": "clove",
        "cloves": "clove",
        "slice": "slice",
        "slices": "slice",
        "large": "large",
        "medium": "medium",
        "small": "small",
    }
    
    WORD_TO_NUMBER = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "a": 1, "an": 1, "half": 0.5, "quarter": 0.25, "third": 0.333,
    }
    
    def __init__(self, db: Session):
        """Initialize parser with database session."""
        self.db = db
        self._ingredient_cache: Optional[Dict] = None
    
    def parse(self, ingredient_text: str) -> ParsedIngredient:        
        warnings = []
        
        # Extract quantity
        quantity, text_after_quantity = self._extract_quantity(ingredient_text)
        if quantity is None:
            quantity = 1.0
            warnings.append("No quantity found, assuming 1")
            text_after_quantity = ingredient_text
        
        # Extract unit
        unit, ingredient_name = self._extract_unit(text_after_quantity)
        if not unit:
            unit = "piece"
            warnings.append("No unit found, assuming piece")
        
        # Clean ingredient name
        ingredient_name = self._clean_ingredient_name(ingredient_name)
        
        # Match to canonical ingredient
        matched_ingredient, confidence = self._match_ingredient(ingredient_name)
        
        if confidence < 0.7:
            warnings.append(f"Low confidence match ({confidence:.2f})")
        
        # Convert to grams
        mass_g = self._convert_to_grams(
            quantity, unit, ingredient_name, matched_ingredient
        )
        
        if mass_g == 0:
            warnings.append("Could not determine mass, using 0g")
        
        return ParsedIngredient(
            original_text=ingredient_text,
            quantity=quantity,
            unit=unit,
            ingredient_name=matched_ingredient.name if matched_ingredient else ingredient_name,
            ingredient_id=matched_ingredient.id if matched_ingredient else None,
            mass_g=mass_g,
            confidence=confidence,
            warnings=warnings
        )
    
    def _extract_quantity(self, text: str) -> Tuple[Optional[float], str]:
        """Extract quantity from ingredient text."""
        text = text.strip()
        
        
        unit_pattern = r"(?:g|kg|mg|ml|l|oz|lb|lbs|tbsp|tsp|cup|cups)\b"
        match = re.match(rf"^(\d+\.?\d*)({unit_pattern})(.*)$", text, re.IGNORECASE)
        if match:
            quantity = float(match.group(1))
            unit = match.group(2)
            remainder = match.group(3).strip()
            return quantity, f"{unit} {remainder}" if remainder else unit
        
        match = re.match(r"^(\d+\.?\d*)\s+(.+)$", text)
        if match:
            return float(match.group(1)), match.group(2)
        
        match = re.match(r"^(\d+)/(\d+)\s+(.+)$", text)
        if match:
            fraction = Fraction(int(match.group(1)), int(match.group(2)))
            return float(fraction), match.group(3)
        
        match = re.match(r"^(\d+)\s+(\d+)/(\d+)\s+(.+)$", text)
        if match:
            whole = int(match.group(1))
            fraction = Fraction(int(match.group(2)), int(match.group(3)))
            return float(whole + fraction), match.group(4)
        for word, num in self.WORD_TO_NUMBER.items():
            pattern = rf"^{word}\s+(.+)$"
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return num, match.group(1)
        
        if text.lower().startswith(("a pinch", "pinch")):
            return 0.5, re.sub(r"^(a\s+)?pinch\s+of\s+", "", text, flags=re.IGNORECASE)
        
        return None, text
    
    def _extract_unit(self, text: str) -> Tuple[Optional[str], str]:
        """Extract unit from ingredient text."""
        text = text.strip().lower()
        
        for unit_name, factor in self.WEIGHT_UNITS.items():
            pattern = rf"^{re.escape(unit_name)}\b\s*(.+)$"
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return unit_name, match.group(1)
        
        for unit_name, ml in self.VOLUME_UNITS.items():
            pattern = rf"^{re.escape(unit_name)}\b\s*(.+)$"
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return unit_name, match.group(1)
        
        for unit_name, canonical in self.COUNT_UNITS.items():
            pattern = rf"^{re.escape(unit_name)}\b\s*(.+)$"
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return canonical, match.group(1)
        
        return None, text
    
    def _clean_ingredient_name(self, name: str) -> str:
        """Clean and normalize ingredient name."""
        name = name.strip()
        
        # Remove common descriptors
        descriptors = [
            r"\bfresh\b", r"\bdried\b", r"\bfrozen\b", r"\bcanned\b",
            r"\braw\b", r"\bcooked\b", r"\bchopped\b", r"\bdiced\b",
            r"\bsliced\b", r"\bminced\b", r"\bground\b", r"\bshredded\b",
            r"\bpeeled\b", r"\bseeded\b", r"\bwashed\b", r"\btrimmed\b",
        ]
        
        for descriptor in descriptors:
            name = re.sub(descriptor, "", name, flags=re.IGNORECASE)
        
        # Remove parenthetical notes
        name = re.sub(r"\([^)]*\)", "", name)
        
        # Clean whitespace
        name = re.sub(r"\s+", " ", name).strip()
        
        return name
    
    def _match_ingredient(self, ingredient_name: str) -> Tuple[Optional[Ingredient], float]:
        """Match ingredient name to database using fuzzy matching."""
        if not ingredient_name:
            return None, 0.0
        
        ingredient_name_lower = ingredient_name.lower()
        
        # Build ingredient cache
        if self._ingredient_cache is None:
            self._build_ingredient_cache()
        
        # Exact match on ingredient name
        if ingredient_name_lower in self._ingredient_cache:
            return self._ingredient_cache[ingredient_name_lower], 1.0
        
        # Exact match on synonyms
        synonyms = self.db.query(IngredientSynonym).filter(
            IngredientSynonym.synonym == ingredient_name_lower
        ).all()
        
        if synonyms:
            best_synonym = max(synonyms, key=lambda s: s.confidence)
            return best_synonym.ingredient, best_synonym.confidence
        
        # Fuzzy matching
        best_match = None
        best_score = 0.0
        
        # Get all ingredients and synonyms for fuzzy matching
        ingredients = self.db.query(Ingredient).all()
        
        for ingredient in ingredients:
            dist = levenshtein_distance(ingredient_name_lower, ingredient.name.lower())
            max_len = max(len(ingredient_name_lower), len(ingredient.name))
            similarity = 1.0 - (dist / max_len) if max_len > 0 else 0.0
            
            if similarity > best_score:
                best_score = similarity
                best_match = ingredient
            
            # Check synonyms
            for synonym in ingredient.synonyms:
                dist = levenshtein_distance(ingredient_name_lower, synonym.synonym.lower())
                max_len = max(len(ingredient_name_lower), len(synonym.synonym))
                similarity = 1.0 - (dist / max_len) if max_len > 0 else 0.0
                
                if similarity > best_score:
                    best_score = similarity * synonym.confidence
                    best_match = ingredient
        
        return best_match, best_score
    
    def _build_ingredient_cache(self) -> None:
        """Build cache of ingredients by name."""
        self._ingredient_cache = {}
        ingredients = self.db.query(Ingredient).all()
        
        for ingredient in ingredients:
            self._ingredient_cache[ingredient.name.lower()] = ingredient
    
    def _convert_to_grams(
        self, 
        quantity: float, 
        unit: str, 
        ingredient_name: str,
        matched_ingredient: Optional[Ingredient]
    ) -> float:
        """Convert quantity and unit to grams."""
        # If already in weight units, convert directly
        if unit in self.WEIGHT_UNITS:
            return quantity * self.WEIGHT_UNITS[unit]
        
        # If volume unit, need density
        if unit in self.VOLUME_UNITS:
            ml = quantity * self.VOLUME_UNITS[unit]
            
            # Check for specific ingredient conversion
            if matched_ingredient and matched_ingredient.id:
                conversion = self.db.query(UnitConversion).filter(
                    UnitConversion.ingredient_id == matched_ingredient.id,
                    UnitConversion.unit == unit
                ).first()
                
                if conversion:
                    return quantity * conversion.grams
            
            # Use density if available
            if matched_ingredient and matched_ingredient.density_g_per_ml:
                return ml * matched_ingredient.density_g_per_ml
            
            # Default density (assume water-like)
            logger.warning(
                f"No density for {ingredient_name}, using default 1.0 g/ml"
            )
            return ml * 1.0
        
        # Count/piece units - need lookup table
        if unit in ["piece", "clove", "slice", "large", "medium", "small"]:
            if matched_ingredient and matched_ingredient.id:
                conversion = self.db.query(UnitConversion).filter(
                    UnitConversion.ingredient_id == matched_ingredient.id,
                    UnitConversion.unit == unit
                ).first()
                
                if conversion:
                    return quantity * conversion.grams
            
            logger.warning(
                f"No conversion for {unit} of {ingredient_name}, using 100g default"
            )
            return quantity * 100.0
        
        logger.error(f"Unknown unit: {unit}")
        return 0.0
