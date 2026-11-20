# syntax=docker/dockerfile:1.7
# ---------- Étape 1 : pipeline (pandas/openpyxl) -> data/processed ----------
FROM python:3.12-slim AS pipeline
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt requirements-pipeline.txt ./
RUN pip install -r requirements-pipeline.txt
COPY src ./src
COPY data/raw ./data/raw
COPY data/reference ./data/reference
ENV PYTHONPATH=/app/src
RUN python -m planner.pipeline

# ---------- Étape 2 : runtime API (sans pandas) ----------
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src PLANNER_DATA_DIR=/app/data PLANNER_ENVIRONMENT=production
COPY requirements.txt ./
RUN pip install -r requirements.txt && useradd --create-home --uid 10001 app
COPY src ./src
COPY --from=pipeline /app/data/processed ./data/processed
USER app
EXPOSE 8000
# PORT est fourni par certains hébergeurs (Render, Railway…) ; 8000 par défaut.
ENV PORT=8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/v1/health').status==200 else 1)"
CMD ["sh", "-c", "exec uvicorn planner.api.app:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*'"]
