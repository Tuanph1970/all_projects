FROM python:3.11-slim

WORKDIR /app

# Install stock-common package
COPY stock-common /tmp/stock-common
RUN pip install --no-cache-dir /tmp/stock-common && rm -rf /tmp/stock-common

# Install service dependencies
COPY services/ai-insights-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/ai-insights-service/app/ ./app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8005

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
