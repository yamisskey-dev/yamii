# Multi-stage build for production-ready yamii server
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies with uv
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r yamii \
    && useradd -r -g yamii yamii

# Set work directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY yamii/ ./yamii/
COPY README.md ./

# Create directories for data persistence
RUN mkdir -p /app/data /app/.yamii_keys && chown -R yamii:yamii /app

# Switch to non-root user
USER yamii

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Expose port
EXPOSE 8000

# Run with FastAPI CLI (Bot auto-starts via lifespan)
CMD ["fastapi", "run", "yamii/api/main.py", "--host", "0.0.0.0", "--port", "8000"]