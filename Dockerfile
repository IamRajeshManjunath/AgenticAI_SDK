# ── Stage 1: Builder ──────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    build-essential gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --user --no-cache-dir -e ".[postgres]" && \
    pip install --user --no-cache-dir gunicorn

# ── Stage 2: Runtime ─────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create data directory for SQLite (dev) and config persistence
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with Gunicorn + Uvicorn workers for production
CMD ["gunicorn", "agenticai_sdk.gateway.app:create_app()", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--max-requests", "10000", \
     "--max-requests-jitter", "1000"]
