"""Layer 1: baseline estimate. Uses real CulinAIAPP-Layer1 when DB is configured."""

from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)

# Lazy: real implementation only when Layer 1 DB env vars are set
_layer1_available: Optional[bool] = None


def _build_ingredients(item_name: str, description: str, modifiers: Optional[List[str]]) -> List[str]:
    """Build ingredient list for Layer 1 parser from item_name, description, modifiers."""
    parts = [item_name]
    if description and description.strip():
        parts.append(description.strip())
    if modifiers:
        parts.extend(m for m in modifiers if m and str(m).strip())
    # Dedupe and filter empty
    seen = set()
    out = []
    for p in parts:
        p = str(p).strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out if out else [item_name or "unknown"]


def _stub_estimate(
    item_name: str,
    description: str,
    modifiers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Fallback when real Layer 1 is unavailable."""
    return {
        "macros": {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0},
        "confidence": 1.0,
    }


def _run_layer1_real(
    item_name: str,
    description: str,
    modifiers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Call real Layer 1 (parser + calculator + DB). Returns Layer1Output shape."""
    from layer1_app.db.session import SessionLocal
    from layer1_app.services.parser import IngredientParser
    from layer1_app.services.calculator import NutrientCalculator

    ingredients = _build_ingredients(item_name, description, modifiers)
    db = SessionLocal()
    try:
        parser = IngredientParser(db)
        calculator = NutrientCalculator(db)
        parsed = [parser.parse(ing) for ing in ingredients]
        totals, _ = calculator.calculate_recipe(parsed, cooking_method=None)
        # Map Layer 1 NutrientTotals to our contract: calories, protein, carbs, fat
        macros = {
            "calories": float(totals.calories or 0.0),
            "protein": float(totals.protein_g or 0.0),
            "carbs": float(totals.carbohydrates_g or 0.0),
            "fat": float(totals.fat_g or 0.0),
        }
        conf = sum(p.confidence for p in parsed) / len(parsed) if parsed else 0.8
        return {"macros": macros, "confidence": min(1.0, max(0.0, conf))}
    finally:
        db.close()


def _is_layer1_configured() -> bool:
    """True if Layer 1 DB env vars are set so we can use the real implementation."""
    import os
    return bool(os.environ.get("DATABASE_URL") and os.environ.get("SECRET_KEY"))


def estimate(
    item_name: str,
    description: str,
    modifiers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Baseline nutrition estimate. Returns dict with 'macros' and 'confidence'.
    Uses real Layer 1 (parser + calculator + DB) when DATABASE_URL and SECRET_KEY are set;
    otherwise returns stub values.
    """
    global _layer1_available
    if _layer1_available is None:
        _layer1_available = False
        if _is_layer1_configured():
            try:
                from layer1_app.core.config import get_settings
                get_settings()
                _layer1_available = True
                logger.info("Layer 1 (real): using DB-backed parser and calculator")
            except Exception as e:
                logger.warning("Layer 1 (real) unavailable: %s; using stub", e)

    if _layer1_available:
        try:
            return _run_layer1_real(item_name, description, modifiers)
        except Exception as e:
            logger.warning("Layer 1 request failed: %s; falling back to stub", e)
    return _stub_estimate(item_name, description, modifiers)
