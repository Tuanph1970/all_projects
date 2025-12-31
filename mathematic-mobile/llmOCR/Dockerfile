# Multi-stage build for Python FastAPI ML service
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 python && \
    adduser --system --uid 1001 --ingroup python python

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM base as production

# Copy application code
COPY --chown=python:python . .

# Create necessary directories
RUN mkdir -p /app/models /app/logs && \
    chown -R python:python /app

# Switch to non-root user
USER python

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8002"]

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black isort flake8 mypy jupyter

# Copy application code
COPY --chown=python:python . .

# Create necessary directories
RUN mkdir -p /app/models /app/logs && \
    chown -R python:python /app

# Switch to non-root user
USER python

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV API_DEBUG=true
ENV LOG_LEVEL=DEBUG

# Expose ports
EXPOSE 8002

# Start with hot reload for development
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]