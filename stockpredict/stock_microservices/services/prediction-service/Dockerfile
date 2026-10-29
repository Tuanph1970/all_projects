FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for ML libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY services/prediction-service/requirements.txt .

# Backlog #109 — CPU-only torch FIRST, so the `darts[torch]` extra in
# requirements.txt finds the dependency satisfied and adds only
# pytorch-lightning / torchmetrics rather than resolving the CUDA stack
# (nvidia-cublas, cudnn, nccl, cusparse ...), which would add ~2.5-3GB for no
# benefit on a CPU trainer. Confirmed by dry-run: with this line the extra
# installs no torch and no CUDA wheels. Remove it to go GPU — the host has an
# RTX 3060 and the nvidia Docker runtime is already available.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

RUN pip install --no-cache-dir -r requirements.txt

COPY stock-common /app/stock-common
RUN pip install -e /app/stock-common

COPY services/prediction-service/app/ ./app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
