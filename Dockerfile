FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    VERISENSE_AUTOSEED=0 \
    VERISENSE_MOCK_MODE=inprocess \
    VERISENSE_REFERENCE_DATE=2026-10-26 \
    VERISENSE_FRONTEND_DIR=/app/frontend/dist \
    OMP_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/backend/.venv/bin:$PATH"
COPY backend/ ./
COPY samples/ /app/samples/
COPY --from=frontend /build/frontend/dist/ /app/frontend/dist/
# Expensive OCR/seeding happens during image build, not on the first web request.
# Stored file paths match /data, the runtime volume's fixed mount point.
RUN VERISENSE_DB=/data/verisense.db VERISENSE_STORAGE=/data/storage python -m seed.seed \
    && VERISENSE_DB=/data/verisense.db VERISENSE_STORAGE=/data/storage python -m seed.seed --refresh \
    && python -c "from app.db import get_engine; get_engine().dispose(); import sqlite3; c=sqlite3.connect('/data/verisense.db'); c.execute('PRAGMA wal_checkpoint(TRUNCATE)'); c.close()" \
    && python -c "import shutil; shutil.move('/data', '/opt/verisense-demo')"
RUN useradd --create-home --uid 1000 verisense \
    && mkdir /data && chown verisense:verisense /data
USER verisense
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','7860')+'/api/health/ready', timeout=8)"
CMD ["python", "serve.py"]
