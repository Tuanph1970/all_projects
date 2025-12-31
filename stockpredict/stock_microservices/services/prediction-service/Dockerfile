FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for ML libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY services/prediction-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY stock-common /app/stock-common
RUN pip install -e /app/stock-common

COPY services/prediction-service/app/ ./app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
