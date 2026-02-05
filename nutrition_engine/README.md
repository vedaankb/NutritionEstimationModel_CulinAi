# Nutrition Estimation Engine

Single in-process service that runs three ML layers in order: **Layer 1 → Layer 2 → Layer 3**. All artifacts are loaded once at startup; every request is deterministic and avoids disk/network in the request path.

## End-to-end request flow

1. **Client** sends `POST /estimate` with a `NutritionRequest` (item_name, description, optional restaurant, price, modifiers).
2. **API** (`app/main.py`) normalizes the request into a cache key (item_name, description, modifiers, restaurant; price is not part of the key).
3. **Cache** (`app/cache.py`): on hit, the cached response is returned; on miss, the pipeline runs.
4. **Pipeline** (`app/engine.py`):
   - **Layer 1** — baseline nutrition estimate from item name, description, modifiers.
   - **Layer 2** — restaurant/price calibration using preloaded calibration tables.
   - **Layer 3** — similarity-based refinement using preloaded embeddings.
5. Confidence is computed with the fixed v1 rule: `0.5*L1 + 0.3*L2 + 0.2*L3`.
6. Response is `NutritionResponse`: `macros`, `confidence`, `debug` (layer2 adjustments, layer3 refinements).

No branching: every request goes through all three layers. No HTTP or LLM calls between layers; no training or per-request disk access.

## Layer responsibilities

| Layer | Role | Artifacts (loaded at startup) |
|-------|------|-------------------------------|
| **Layer 1** | Baseline estimate from item name + description + modifiers | None (in-code or bundled in layer repo) |
| **Layer 2** | Restaurant/price calibration | `artifacts/layer2/` — calibration tables |
| **Layer 3** | Similarity refinement | `artifacts/layer3/` — embeddings |

- **Layer 1** is **integrated in-repo**: `layers/layer1/` contains an adapter and the real [CulinAIAPP-Layer1](https://github.com/arjunpkulkarni/CulinAIAPP-Layer1) code (as `layer1_app`). When `DATABASE_URL` and `SECRET_KEY` are set, the engine uses the DB-backed parser and calculator; otherwise it uses a stub.
- **Layer 2** is **integrated in-repo**: `layers/layer2/` contains the real [CulinAIAPP-Layer2](https://github.com/vedaankb/CulinAIAPP-Layer2) code. Place `trained_model.pkl` in `artifacts/layer2/` (or train your own via the Layer 2 repo); if missing, calibration uses a fallback (baseline passed through, low confidence).
- **Layer 3** is **integrated in-repo**: `layers/layer3/` contains the real [CulinAIAPP-Layer3](https://github.com/vedaankb/CulinAIAPP-Layer3) code. Place Layer 3 artifacts in `artifacts/layer3/` (build via the Layer 3 repo’s `layer3_artifact_build.ipynb`: `ingredient_embeddings.pkl`, `dish_embeddings.pkl`, `neighbor_index.pkl`, `macro_delta_stats.json`, `confidence_params.json`). If artifacts are missing, refinement passes through L2 macros.

**Layer 1 (real):** To use the real Layer 1 (parser + nutrient calculator):

1. Set environment variables: `DATABASE_URL` (PostgreSQL connection string), `SECRET_KEY` (any string; required by Layer 1 config).
2. Install Layer 1 dependencies: `pip install -r requirements-layer1.txt`. Ensure the Layer 1 DB is migrated and seeded (USDA data, ingredients, etc.).
3. Run `python -m spacy download en_core_web_sm` for the parser.

If `DATABASE_URL` or `SECRET_KEY` is unset, Layer 1 falls back to a stub (zeros for macros, 1.0 confidence).

**Layer 2 (real):** Put `trained_model.pkl` in `artifacts/layer2/`. The repo ships a pre-trained model in the Layer 2 source; copy it or train your own with the [Layer 2 repo](https://github.com/vedaankb/CulinAIAPP-Layer2).

**Layer 3 (real):** Build artifacts with the [Layer 3 repo](https://github.com/vedaankb/CulinAIAPP-Layer3) (e.g. run `layer3_artifact_build.ipynb`), then copy the generated files into `artifacts/layer3/`. Requires `numpy` (in main `requirements.txt`).

## Startup vs request-time behavior

- **Startup** (`app/startup.py`):
  - Load Layer 2 calibration tables from `artifacts/layer2`.
  - Load Layer 3 embeddings from `artifacts/layer3`.
  - Optional cache warmup.
- **Request time**:
  - No disk reads.
  - No model or artifact loading.
  - Single in-memory path: cache lookup → if miss, Layer 1 → Layer 2 → Layer 3 → cache store → return.

## How to update artifacts

- **Layer 2**: Replace or add files under `artifacts/layer2/`. Restart the service so `load_calibration_tables()` runs again at startup.
- **Layer 3**: Replace or add files under `artifacts/layer3/`. Restart the service so `load_embeddings()` runs again at startup.

Artifact root can be overridden with the `NUTRITION_ARTIFACTS` environment variable (default: `artifacts`).

**Git:** Artifact binaries (`.pkl`, Layer 3 `.json`) are in `.gitignore`; supply them at deploy (e.g. mount a volume or add in CI). To ship the Layer 2 model in the repo, adjust `.gitignore` and commit `artifacts/layer2/trained_model.pkl`.

## Production run (Docker) — recommended

Low-latency, production-ready image with Gunicorn + Uvicorn workers, health checks, and structured logging.

```bash
# Build (from nutrition_engine directory)
docker build -t nutrition-engine .

# Run (default: 2 workers, port 8000)
docker run -p 8000:8000 nutrition-engine

# With custom artifacts dir (e.g. mounted volume) and 4 workers
docker run -p 8000:8000 -v /path/to/artifacts:/app/artifacts -e NUTRITION_WORKERS=4 nutrition-engine
```

**Endpoints**

- **POST /estimate** — main API (JSON body: `NutritionRequest`).
- **GET /health** — liveness (returns 200 when process is up; use for load balancer pings).
- **GET /ready** — readiness (returns 200 after startup; use for Kubernetes/orchestrator readiness probe).

**Environment (optional)**

| Variable | Default | Description |
|----------|---------|-------------|
| `NUTRITION_ARTIFACTS` | `artifacts` | Path to artifacts dir (layer2 + layer3 data). |
| `NUTRITION_CACHE_MAXSIZE` | `10000` | LRU cache size. |
| `NUTRITION_WORKERS` | `2` | Gunicorn worker count (each loads L2/L3 at startup). |

## How to deploy to cloud

1. **Docker (recommended)**  
   Build the image above; run on Cloud Run, ECS, EKS, or any container host. Point readiness probe at `GET /ready`, liveness at `GET /health`.

2. **Bare Python**  
   - Install: `pip install -r requirements.txt`  
   - Layers: `git submodule update --init --recursive`  
   - Artifacts: ensure `artifacts/layer2` and `artifacts/layer3` are present.  
   - Run with Gunicorn (production):  
     `gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`  
   - Or single process: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

3. **Optional env** (same as table above): `NUTRITION_ARTIFACTS`, `NUTRITION_CACHE_MAXSIZE`, `NUTRITION_WORKERS`.

## Performance targets

- Layer 1: ~5–10 ms  
- Layer 2: ~5–8 ms  
- Layer 3: ~8–15 ms  
- **Total (cold)**: ≤35 ms per request  
- **Cache hit**: <10 ms  
