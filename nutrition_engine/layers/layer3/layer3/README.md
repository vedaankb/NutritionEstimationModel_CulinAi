# Layer 3: Refinement (runtime)

Layer 3 takes **input from Layer 1 or Layer 2** and **refines macros** using embeddings and similarity neighborhoods. Artifacts are built offline by `layer3_artifact_build.ipynb`; this package is **read-only inference**.

## Input (from Layer 1 or Layer 2)

- `ingredients`: list of ontology-normalized ingredient names
- `cooking_methods`: list of ontology-normalized cooking methods
- `sauces`: float 0–1
- `portion_class`: `"small"` | `"medium"` | `"large"`
- `initial_macros` (optional): `{calories, fat, carbs, protein, sodium}` from Layer 1/2

## Output

- **Refined macros**: bounded adjustments using similar dishes and `macro_delta_stats` (p10–p90)
- **Confidence**: from similarity and ingredient coverage (lookup only)
- **Similar dish IDs**: top-k neighbors used for refinement

## Usage

```python
from pathlib import Path
from layer3 import refine

result = refine(
    ingredients=["chicken breast", "rice", "broccoli"],
    cooking_methods=["baked", "steamed"],
    sauces=0.2,
    portion_class="medium",
    initial_macros={"calories": 400, "fat": 12, "carbs": 45, "protein": 35, "sodium": 500},
    artifacts_dir=Path("artifacts"),
)
print(result.refined_macros, result.confidence, result.similar_dish_ids)
```

## Modules

- **loader**: loads `ingredient_embeddings.pkl`, `dish_embeddings.pkl`, `neighbor_index.pkl`, `macro_delta_stats.json`, `confidence_params.json`
- **embeddings**: embed a dish from ingredients + methods + sauce + portion (same formula as notebook)
- **similarity**: cosine similarity, top-k similar dishes
- **refinement**: bounded macro refinement (p10–p90 from `macro_delta_stats`)
- **confidence**: similarity → confidence, ingredient coverage → penalty (scalars/lookup only)

## Prerequisites

1. Run `layer3_artifact_build.ipynb` to produce `artifacts/`.
2. Use the same ontology for ingredients and cooking methods as in the notebook.

## Production (L1 → L2 → L3)

Your app calls Layer 1 and Layer 2 (in their repos), then Layer 3. **Load artifacts once at startup** and pass them into every `refine()` call so you don’t hit disk per request:

```python
from pathlib import Path
from layer3 import refine, loader

_artifacts = loader.load_all(Path("artifacts"))

result = refine(
    ingredients=l2_output["ingredients"],
    cooking_methods=l2_output["cooking_methods"],
    sauces=l2_output["sauces"],
    portion_class=l2_output["portion_class"],
    initial_macros=l2_output.get("initial_macros"),
    artifacts=_artifacts,
)
# result.refined_macros, result.confidence
```

See **`docs/PRODUCTION.md`** for the full L1/L2/L3 contract, deployment, and production checklist.
