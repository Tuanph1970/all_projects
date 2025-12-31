# Phase 2: Microservices Implementation Plan

## Overview

Phase 2 implements the 7 microservices that will gradually replace the Django monolith using the **Strangler Fig pattern**. Each service is a FastAPI application using the shared `stock-common` library.

## Architecture Summary

```
                    ┌─────────────────┐
                    │     Traefik     │
                    │  (API Gateway)  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  auth-service │   │ stock-data    │   │  portfolio    │
│    :8007      │   │   :8001       │   │    :8003      │
└───────────────┘   └───────────────┘   └───────────────┘
        │                    │                    │
        │           ┌────────┼────────┐          │
        │           │        │        │          │
        ▼           ▼        ▼        ▼          ▼
┌───────────────┐ ┌─────────────────┐ ┌───────────────┐
│  prediction   │ │    analysis     │ │  ai-insights  │
│    :8002      │ │     :8004       │ │    :8005      │
└───────────────┘ └─────────────────┘ └───────────────┘
                          │
                          ▼
                 ┌───────────────┐
                 │   chatbot     │
                 │    :8006      │
                 └───────────────┘
```

## Service Implementation Order

### Phase 2.1: Foundation Services
1. **auth-service** - User authentication, JWT tokens, registration
2. **stock-data-service** - Stock data, companies, market info

### Phase 2.2: Core Business Services
3. **portfolio-service** - Portfolio management, transactions, alerts
4. **prediction-service** - ML models, training, predictions

### Phase 2.3: Analytics Services
5. **analysis-service** - Technical/fundamental analysis, screener
6. **ai-insights-service** - AI-powered insights, patterns, sentiment

### Phase 2.4: User Interaction
7. **chatbot-service** - Conversational AI interface

---

## Service Specifications

### 1. auth-service (Port 8007)

**Responsibility**: User authentication and authorization

**Database**: `auth_db`

**API Endpoints**:
```
POST   /api/v2/auth/login           - User login
POST   /api/v2/auth/register        - User registration
POST   /api/v2/auth/refresh         - Refresh JWT token
POST   /api/v2/auth/logout          - Logout (revoke token)
POST   /api/v2/auth/change-password - Change password
POST   /api/v2/auth/reset-password  - Password reset
GET    /api/v2/auth/me              - Get current user
GET    /api/v2/auth/verify          - Verify token validity
```

**Events Published**:
- `user.registered`
- `user.logged_in`
- `user.password_changed`

**Dependencies**: None (foundation service)

---

### 2. stock-data-service (Port 8001)

**Responsibility**: Stock data, companies, market information

**Database**: `stockdata_db`

**API Endpoints**:
```
# Companies
GET    /api/v2/companies/all              - List all companies
GET    /api/v2/companies/groups/{group}   - Companies by group
GET    /api/v2/companies/industries       - List industries
GET    /api/v2/companies/industry/{id}    - Companies by industry
GET    /api/v2/companies/top-gainers      - Top gainers
GET    /api/v2/companies/top-losers       - Top losers
GET    /api/v2/companies/top-actives      - Most active stocks

# Stock Data
GET    /api/v2/stocks/{symbol}/profile    - Company profile
GET    /api/v2/stocks/{symbol}/overview   - Company overview
GET    /api/v2/stocks/{symbol}/history    - Historical OHLCV data
GET    /api/v2/stocks/{symbol}/news       - Company news
GET    /api/v2/stocks/{symbol}/events     - Corporate events
GET    /api/v2/stocks/{symbol}/dividends  - Dividend history

# Market Data
GET    /api/v2/market/indices             - Market indices
GET    /api/v2/market/priceboard          - Live price board
GET    /api/v2/market/index-series        - Index time series

# Search
GET    /api/v2/stocks/search              - Search stocks
GET    /api/v2/stocks/list                - Paginated stock list
```

**Events Published**:
- `stock.price_updated`
- `stock.data_synced`

**Dependencies**: VNStock API

---

### 3. portfolio-service (Port 8003)

**Responsibility**: Portfolio management, transactions, alerts

**Database**: `portfolio_db`

**API Endpoints**:
```
# Portfolio
GET    /api/v2/portfolio                  - Get user portfolio
GET    /api/v2/portfolio/summary          - Portfolio summary
GET    /api/v2/portfolio/performance      - Performance metrics
GET    /api/v2/portfolio/metrics          - Detailed metrics

# Transactions
POST   /api/v2/portfolio/buy              - Buy stock
POST   /api/v2/portfolio/sell             - Sell stock
POST   /api/v2/portfolio/add              - Add to watchlist
DELETE /api/v2/portfolio/remove           - Remove from portfolio

# Alerts
GET    /api/v2/alerts                     - Get user alerts
POST   /api/v2/alerts                     - Create alert
PUT    /api/v2/alerts/{id}                - Update alert
DELETE /api/v2/alerts/{id}                - Delete alert
POST   /api/v2/alerts/{id}/toggle         - Toggle alert status

# Recommendations
GET    /api/v2/portfolio/recommendations  - Stock recommendations
GET    /api/v2/portfolio/prospective      - Prospective stocks

# Sync
GET    /api/v2/portfolio/sync-status      - Sync status
POST   /api/v2/portfolio/sync/{symbol}    - Trigger sync
```

**Events Consumed**:
- `stock.price_updated` - Check price alerts

**Events Published**:
- `portfolio.transaction_completed`
- `alert.triggered`

**Dependencies**: auth-service, stock-data-service

---

### 4. prediction-service (Port 8002)

**Responsibility**: ML models, training, predictions

**Database**: `prediction_db`

**API Endpoints**:
```
# Models
GET    /api/v2/models                     - List available models
GET    /api/v2/models/types               - Model types
GET    /api/v2/models/{id}                - Get model details
GET    /api/v2/models/parameters          - Model parameters
GET    /api/v2/models/parameters/default  - Default parameters
DELETE /api/v2/models/{id}                - Delete model

# Solutions
GET    /api/v2/solutions                  - List solutions
GET    /api/v2/solutions/{id}             - Get solution
POST   /api/v2/solutions                  - Create solution
PUT    /api/v2/solutions/{id}             - Update solution
DELETE /api/v2/solutions/{id}             - Delete solution

# Training & Prediction
POST   /api/v2/solutions/{id}/train       - Train solution
GET    /api/v2/solutions/{id}/status      - Training status
POST   /api/v2/solutions/{id}/predict     - Run prediction

# Time Series
GET    /api/v2/timeseries                 - List time series
POST   /api/v2/timeseries                 - Create time series
PUT    /api/v2/timeseries/{id}            - Update time series
DELETE /api/v2/timeseries/{id}            - Delete time series

# Indicators
GET    /api/v2/indicators                 - List indicators
GET    /api/v2/indicators/type/{type}     - Indicators by type
POST   /api/v2/indicators/calculate       - Calculate indicators
GET    /api/v2/solutions/{id}/indicators  - Solution indicators
POST   /api/v2/solutions/{id}/indicators  - Set solution indicators
```

**Events Published**:
- `model.training_started`
- `model.training_completed`
- `prediction.generated`

**Dependencies**: auth-service, stock-data-service

---

### 5. analysis-service (Port 8004)

**Responsibility**: Technical and fundamental analysis

**Database**: Uses `stockdata_db` (read-only)

**API Endpoints**:
```
# Technical Analysis
GET    /api/v2/analysis/technical/{symbol}           - Full technical analysis
GET    /api/v2/analysis/technical/{symbol}/indicators - Technical indicators
GET    /api/v2/analysis/technical/{symbol}/intraday  - Intraday analysis

# Fundamental Analysis
GET    /api/v2/analysis/fundamental/{symbol}         - Full fundamental analysis
GET    /api/v2/analysis/fundamental/{symbol}/statements - Financial statements
GET    /api/v2/analysis/fundamental/compare          - Compare companies

# Industries
GET    /api/v2/industries                            - List industries
GET    /api/v2/industries/{code}/stocks              - Industry stocks
GET    /api/v2/industries/{code}/analysis            - Industry analysis
GET    /api/v2/industries/{code}/performance         - Industry performance
POST   /api/v2/industries/compare                    - Compare industries

# Stock Screener
POST   /api/v2/screener                              - Screen stocks
GET    /api/v2/screener/criteria                     - Screening criteria
POST   /api/v2/screener/advanced                     - Advanced screening
```

**Dependencies**: stock-data-service

---

### 6. ai-insights-service (Port 8005)

**Responsibility**: AI-powered insights and analysis

**API Endpoints**:
```
# AI Insights
GET    /api/v2/ai/overview                - AI insights overview
POST   /api/v2/ai/comprehensive           - Comprehensive AI analysis

# Pattern Recognition
POST   /api/v2/ai/patterns                - Detect chart patterns

# Sentiment Analysis
POST   /api/v2/ai/sentiment               - Analyze sentiment

# Risk Assessment
POST   /api/v2/ai/risk                    - Assess risk

# AI Predictions
POST   /api/v2/ai/predict                 - AI price prediction

# Technical Indicators
POST   /api/v2/ai/indicators              - Calculate indicators
GET    /api/v2/ai/indicators/available    - Available indicators

# AI Score
POST   /api/v2/ai/score                   - Calculate AI score
```

**Dependencies**: stock-data-service, prediction-service, Groq API

---

### 7. chatbot-service (Port 8006)

**Responsibility**: Conversational AI interface

**API Endpoints**:
```
# Chat
POST   /api/v2/chatbot/ask                - Ask question
GET    /api/v2/chatbot/capabilities       - Bot capabilities
GET    /api/v2/chatbot/categories         - Question categories
POST   /api/v2/chatbot/feedback           - Provide feedback
GET    /api/v2/chatbot/health             - Health check
```

**Dependencies**: All other services (orchestrates queries)

---

## Common Service Structure

Each service follows this structure:

```
services/{service-name}/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Service configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py        # API routes
│   │   └── dependencies.py  # Route dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   ├── domain.py        # Domain models
│   │   └── schemas.py       # Pydantic schemas
│   ├── services/
│   │   ├── __init__.py
│   │   └── {service}.py     # Business logic
│   └── repositories/
│       ├── __init__.py
│       └── {repo}.py        # Data access
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_{service}.py
```

---

## Implementation Checklist

### Per-Service Checklist

- [ ] Create service directory structure
- [ ] Create Dockerfile
- [ ] Create requirements.txt
- [ ] Implement FastAPI main.py with:
  - [ ] Health endpoints (/health/live, /health/ready)
  - [ ] Metrics endpoint (/metrics)
  - [ ] OpenAPI documentation
- [ ] Implement API routes
- [ ] Implement business logic services
- [ ] Implement repository layer
- [ ] Add Pydantic schemas
- [ ] Configure observability (tracing, logging, metrics)
- [ ] Add to docker-compose.yml
- [ ] Test endpoints
- [ ] Update Traefik routing

---

## Technology Stack

- **Framework**: FastAPI 0.109+
- **Database**: MySQL 8.0 with asyncmy
- **ORM**: SQLAlchemy 2.0 (async)
- **Validation**: Pydantic v2
- **HTTP Client**: httpx (async)
- **Message Queue**: RabbitMQ with aio-pika
- **Cache**: Redis with aioredis
- **Tracing**: OpenTelemetry + Jaeger
- **Metrics**: Prometheus
- **Authentication**: JWT (PyJWT)

---

## Migration Strategy

### Phase 2.1: Shadow Mode
- New services run alongside Django
- Traffic still goes to Django
- Services sync data from Django DB

### Phase 2.2: Gradual Cutover
- Route specific endpoints to microservices
- Monitor for errors and performance
- Rollback capability via Traefik

### Phase 2.3: Full Migration
- All traffic to microservices
- Django serves as fallback only
- Eventually decommission Django

---

## Environment Variables

Each service uses these environment variables:

```env
# Service Identity
SERVICE_NAME=auth-service
SERVICE_VERSION=1.0.0
ENVIRONMENT=development

# Database
DATABASE_HOST=mysql
DATABASE_PORT=3306
DATABASE_USER=root
DATABASE_PASSWORD=Mysql_2025
DATABASE_NAME=auth_db

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=stockuser
RABBITMQ_PASSWORD=stockpass
RABBITMQ_VHOST=/stock

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Tracing
TRACING_ENABLED=true
TRACING_JAEGER_HOST=jaeger
TRACING_JAEGER_PORT=6831

# Service Discovery
AUTH_SERVICE_URL=http://auth-service:8007
STOCK_DATA_SERVICE_URL=http://stock-data-service:8001
# ... etc
```

---

## Success Criteria

1. All 7 services running and healthy
2. API endpoints responding correctly
3. Inter-service communication working
4. Authentication/authorization working
5. Observability stack collecting metrics
6. Zero downtime during migration
7. Performance equal or better than monolith

---

## Timeline

| Week | Deliverable |
|------|-------------|
| 1 | auth-service + stock-data-service |
| 2 | portfolio-service + prediction-service |
| 3 | analysis-service + ai-insights-service |
| 4 | chatbot-service + Integration testing |

---

## Next Steps

1. Create service directory structure
2. Implement auth-service first
3. Test with existing frontend
4. Iterate through remaining services
