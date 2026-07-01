FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY services/event-reaction-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY stock-common /app/stock-common
RUN pip install -e /app/stock-common

# The event-reaction stats stages reuse chart_decomp helpers (vol/surrogates).
COPY chart-decomp-lib /app/chart-decomp-lib
RUN pip install -e /app/chart-decomp-lib

COPY event-reaction-lib /app/event-reaction-lib
RUN pip install -e /app/event-reaction-lib

COPY services/event-reaction-service/app/ ./app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8012

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8012"]
