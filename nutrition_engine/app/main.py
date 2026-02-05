"""FastAPI entry. Single public endpoint: POST /estimate. Production: health + ready."""

import logging
import time

from fastapi import FastAPI, Request
from app.schemas import NutritionRequest
from app.cache import cached_estimate
from app.startup import startup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nutrition Estimation Engine", version="1.0.0")


@app.on_event("startup")
def on_startup():
    startup(app)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s %s %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/health")
def health():
    """Liveness: process is up. Use for load balancer pings."""
    return {"status": "ok"}


@app.get("/ready")
def ready(request: Request):
    """Readiness: startup finished and this worker can accept traffic."""
    if getattr(request.app.state, "ready", False):
        return {"status": "ready"}
    return {"status": "starting"}, 503


@app.post("/estimate")
def estimate(req: NutritionRequest):
    return cached_estimate(req)
