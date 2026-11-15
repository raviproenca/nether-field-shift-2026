# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
# Product API (apps/api) for Cloud Run. CPU only. Build from the repository root:
#   docker build -t field-shift-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    FORECAST_CACHE_DIR=/tmp/forecast-cache

WORKDIR /app

COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

COPY src ./src
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api ./apps/api
# Snapshots read by /diagnosis, the ZARC tables and the IBGE municipal mesh (no credentials, no .netrc).
COPY apps/web/public/data ./apps/web/public/data
COPY data/reference/zarc ./data/reference/zarc
COPY data/sample/ibge_se_municipalities.geojson ./data/sample/ibge_se_municipalities.geojson

RUN useradd --system --uid 10001 --no-create-home appuser
USER appuser

EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT}"]
