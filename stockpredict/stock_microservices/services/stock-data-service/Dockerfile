# Stock Data Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY services/stock-data-service/requirements.txt .

# Vendored wheels for packages WITHDRAWN from public PyPI (Backlog #96).
# `pip install vnstock==4.0.7` now fails — vnstock and its dependency vnai
# both 404 on PyPI since the vendor moved to a registered, keyed channel for
# generation 5. Builds only kept working because this layer was Docker-cached;
# any requirements.txt change or cache prune would have broken them.
# See vendor/wheels/README.md.
COPY vendor/wheels /tmp/wheels

# Install Python dependencies. --find-links resolves the withdrawn packages
# locally; the public index stays enabled so everything else resolves normally
# (--no-index would also block requests, pandas and the rest).
RUN pip install --no-cache-dir --find-links=/tmp/wheels -r requirements.txt

# Copy stock-common library
COPY stock-common /app/stock-common
RUN pip install -e /app/stock-common

# Copy application code
COPY services/stock-data-service/app/ ./app/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health/live')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
