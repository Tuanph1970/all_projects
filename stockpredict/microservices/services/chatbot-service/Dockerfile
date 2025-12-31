FROM python:3.11-slim

WORKDIR /app

# Install stock-common package
COPY stock-common /tmp/stock-common
RUN pip install --no-cache-dir /tmp/stock-common && rm -rf /tmp/stock-common

# Install service dependencies
COPY services/chatbot-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/chatbot-service/app/ ./app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8006

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
