# syntax=docker/dockerfile:1.6
# Multi-stage build for the Orbital Conjunctions backend.

############################
# 1) Build stage
############################
FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip wheel \
    && pip wheel --wheel-dir /wheels .

############################
# 2) Runtime stage
############################
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OC_ENVIRONMENT=production

RUN useradd --create-home --uid 10001 oc
WORKDIR /app

COPY --from=build /wheels /wheels
RUN pip install --no-index --find-links=/wheels orbital-conjunctions-backend \
    && rm -rf /wheels

COPY alembic.ini ./
COPY alembic ./alembic

USER oc

EXPOSE 8000

CMD ["uvicorn", "oc.main:app", "--host", "0.0.0.0", "--port", "8000"]
