"""Single LRU cache. Key = normalized hash of item_name, description, modifiers, restaurant."""

import json
from functools import lru_cache
from app.engine import estimate_nutrition
from app.schemas import NutritionRequest, NutritionResponse
from app.config import CACHE_MAXSIZE


def _normalize_key(req: NutritionRequest) -> str:
    """Stable string key from item_name, description, modifiers, restaurant (no price)."""
    payload = {
        "item_name": req.get("item_name", ""),
        "description": req.get("description", ""),
        "modifiers": req.get("modifiers") or [],
        "restaurant": req.get("restaurant"),
    }
    return json.dumps(payload, sort_keys=True)


def _request_from_key(cache_key: str) -> NutritionRequest:
    """Reconstruct request dict from cache key for cache-miss path."""
    data = json.loads(cache_key)
    return {
        "item_name": data["item_name"],
        "description": data["description"],
        "modifiers": data["modifiers"] if data["modifiers"] else None,
        "restaurant": data.get("restaurant"),
        "price": None,
    }


@lru_cache(maxsize=CACHE_MAXSIZE)
def _cached_estimate_impl(cache_key: str) -> dict:
    """Internal: hashable cache key only. Deserialize and run pipeline."""
    req = _request_from_key(cache_key)
    return estimate_nutrition(req)


def cached_estimate(req: NutritionRequest) -> NutritionResponse:
    """Return estimate, using LRU cache keyed by normalized request."""
    key = _normalize_key(req)
    return _cached_estimate_impl(key)


def warmup_cache() -> None:
    """Optional warmup: no-op or run a single dummy request to prime layers."""
    pass
