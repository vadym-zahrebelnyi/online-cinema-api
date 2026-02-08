FROM python:3.12.8-slim AS builder

ARG APP_ENV=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ca-certificates \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock configs/alembic/alembic.ini ./

RUN if [ "$APP_ENV" = "dev" ]; then \
        uv sync --frozen ; \
    else \
        uv sync --frozen --no-dev ; \
    fi

COPY src/ ./src
COPY alembic/ ./alembic

FROM python:3.12.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /bin/uv /bin/uv
COPY --from=builder /bin/uvx /bin/uvx

COPY --from=builder /app /app

EXPOSE 8000
