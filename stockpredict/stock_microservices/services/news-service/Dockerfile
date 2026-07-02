FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY services/news-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY stock-common /app/stock-common
RUN pip install -e /app/stock-common

COPY services/news-service/app/ ./app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8013

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8013"]
