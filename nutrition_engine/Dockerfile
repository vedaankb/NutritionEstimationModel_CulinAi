# Production image: low-latency nutrition estimation engine
# Build: docker build -t nutrition-engine .
# Run:   docker run -p 8000:8000 nutrition-engine

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code and artifacts (layer tables/embeddings go in artifacts/)
COPY app/ ./app/
COPY layers/ ./layers/
COPY artifacts/ ./artifacts/

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Gunicorn + uvicorn workers. Override workers with: docker run -e NUTRITION_WORKERS=4 ...
# Bind 0.0.0.0 for container networking; timeout 30s for slow cold requests
ENV NUTRITION_WORKERS=2
CMD ["sh", "-c", "exec gunicorn app.main:app --workers ${NUTRITION_WORKERS} --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 30 --graceful-timeout 10 --access-logfile - --capture-output"]
