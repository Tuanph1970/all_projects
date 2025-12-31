# =============================================================================
# Stock Predict WebAPI - Docker Image
# =============================================================================
# Multi-stage build for optimized image size
# Supports both CPU and CUDA (GPU) versions

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt

# Install PyTorch CPU version first (smaller image, works on all machines)
# For GPU support, use: --extra-index-url https://download.pytorch.org/whl/cu121
RUN pip install --upgrade pip setuptools wheel && \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r /tmp/requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Final image
# -----------------------------------------------------------------------------
FROM python:3.12-slim as runtime

# Labels
LABEL maintainer="TuanPH" \
      version="1.0" \
      description="Stock Predict Django WebAPI"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=stockapi.settings \
    HOME=/home/stockapi \
    # Fix for libstdc++ compatibility
    LD_LIBRARY_PATH=/opt/venv/lib:$LD_LIBRARY_PATH

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security with home directory
RUN groupadd -r stockapi && useradd -r -g stockapi -m -d /home/stockapi stockapi

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=stockapi:stockapi . .

# Create necessary directories and make entrypoint executable
RUN mkdir -p /app/media /app/static /app/logs /app/model_data /home/stockapi/.vnstock && \
    chmod +x /app/docker-entrypoint.sh && \
    chown -R stockapi:stockapi /app /home/stockapi

# Switch to non-root user
USER stockapi

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/stock/api/ || exit 1

# Default command - run with gunicorn for production
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
