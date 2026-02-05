"""Application configuration. No per-request disk or network."""

import os
from pathlib import Path

# Base path for artifacts (set at startup; no disk read after)
ARTIFACTS_ROOT = Path(os.environ.get("NUTRITION_ARTIFACTS", "artifacts")).resolve()

LAYER2_ARTIFACTS = ARTIFACTS_ROOT / "layer2"
LAYER3_ARTIFACTS = ARTIFACTS_ROOT / "layer3"

CACHE_MAXSIZE = int(os.environ.get("NUTRITION_CACHE_MAXSIZE", "10000"))

# Gunicorn workers (each loads L2/L3 at startup; 2 is a good default for latency + redundancy)
WORKER_COUNT = int(os.environ.get("NUTRITION_WORKERS", "2"))
