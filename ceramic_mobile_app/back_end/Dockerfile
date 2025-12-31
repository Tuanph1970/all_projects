# =============================================================================
# Multi-stage Dockerfile for Python FastAPI Application
# Optimized for both development and production environments
# =============================================================================

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Development Stage
# =============================================================================
FROM base as development

# Copy requirements
COPY requirements.txt .

# Install Python dependencies with development tools
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install pytest pytest-asyncio pytest-cov httpx

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads logs

# Expose port
EXPOSE 8002

# Development command with auto-reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload", "--log-level", "debug"]

# =============================================================================
# Production Stage
# =============================================================================
FROM base as production

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p uploads logs && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Production command with Gunicorn and multiple workers
CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8002", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]

# =============================================================================
# Default to production stage
# To build for development: docker build --target development -t app:dev .
# To build for production: docker build --target production -t app:prod .
# =============================================================================
