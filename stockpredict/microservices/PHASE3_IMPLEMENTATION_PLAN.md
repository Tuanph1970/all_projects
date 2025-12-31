# Phase 3: Migration & Production Readiness Plan

## Overview

Phase 3 completes the migration from Django monolith to microservices using the **Strangler Fig pattern**. This phase focuses on integration testing, shadow mode deployment, gradual traffic cutover, and production hardening.

## Prerequisites (Phase 2 Complete)

- [x] All 7 microservices implemented and running
- [x] Traefik API Gateway configured
- [x] RabbitMQ message broker ready
- [x] Redis caching layer operational
- [x] MySQL databases initialized
- [x] Prometheus + Grafana monitoring stack
- [x] Jaeger distributed tracing
- [x] stock-common shared library

---

## Architecture Overview

```
                         ┌─────────────────────────────┐
                         │      Load Balancer          │
                         │   (Production: nginx/ALB)   │
                         └─────────────┬───────────────┘
                                       │
                         ┌─────────────▼───────────────┐
                         │         Traefik             │
                         │    (API Gateway + Router)   │
                         │  ┌─────────────────────┐   │
                         │  │   Feature Flags     │   │
                         │  │   Traffic Splitter  │   │
                         │  └─────────────────────┘   │
                         └─────────────┬───────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
    ┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐
    │  Microservices  │    │   Shadow Mode       │    │  Django Legacy  │
    │   (Primary)     │◄───│   (Comparison)      │───►│   (Fallback)    │
    └─────────────────┘    └─────────────────────┘    └─────────────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       │
                         ┌─────────────▼───────────────┐
                         │     Shared Databases        │
                         │  (MySQL + Redis + RabbitMQ) │
                         └─────────────────────────────┘
```

---

## Phase 3.1: Integration Testing & Quality Assurance

### 3.1.1 Integration Test Suite

**Objective**: Comprehensive end-to-end testing of all microservices

```
tests/
├── integration/
│   ├── conftest.py                    # Shared fixtures
│   ├── test_auth_flow.py              # Complete auth journey
│   ├── test_stock_data_flow.py        # Stock data retrieval
│   ├── test_portfolio_operations.py   # Portfolio CRUD + transactions
│   ├── test_prediction_pipeline.py    # ML model training + prediction
│   ├── test_analysis_workflow.py      # Technical + fundamental analysis
│   ├── test_ai_insights_flow.py       # AI-powered insights
│   ├── test_chatbot_conversation.py   # Chat interactions
│   └── test_cross_service.py          # Inter-service communication
├── e2e/
│   ├── test_user_journey.py           # Full user workflow
│   ├── test_trading_workflow.py       # Buy/sell flow
│   └── test_analysis_workflow.py      # Research to decision
├── performance/
│   ├── locustfile.py                  # Load testing with Locust
│   ├── test_stress.py                 # Stress testing
│   └── test_spike.py                  # Spike testing
├── contract/
│   ├── test_api_contracts.py          # API schema validation
│   └── pact/                          # Consumer-driven contracts
└── security/
    ├── test_auth_security.py          # Auth vulnerabilities
    ├── test_injection.py              # SQL/NoSQL injection
    └── test_rate_limiting.py          # Rate limit verification
```

**Test Scenarios**:

| Test Category | Scenarios | Priority |
|---------------|-----------|----------|
| Auth Flow | Register → Login → Token Refresh → Logout | P0 |
| Portfolio | Create → Add Holdings → Transaction → Summary | P0 |
| Stock Data | Search → Profile → History → Real-time | P0 |
| Prediction | Create Model → Train → Predict → Validate | P1 |
| Analysis | Technical → Fundamental → Screener | P1 |
| AI Insights | Generate Insight → Compare → News Analysis | P1 |
| Chatbot | Session → Query → Response → History | P2 |
| Cross-Service | Auth → Portfolio → Stock Data → Analysis | P0 |

### 3.1.2 Test Environment Setup

```yaml
# docker-compose.test.yml
version: "3.8"

services:
  test-runner:
    build:
      context: .
      dockerfile: Dockerfile.test
    environment:
      - TEST_ENV=integration
      - DATABASE_HOST=mysql-test
      - REDIS_HOST=redis-test
    depends_on:
      - mysql-test
      - redis-test
      - rabbitmq-test
    volumes:
      - ./tests:/app/tests
      - ./reports:/app/reports

  mysql-test:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: testpass
      MYSQL_DATABASE: test_db
    tmpfs:
      - /var/lib/mysql  # In-memory for speed

  redis-test:
    image: redis:7.2-alpine
    command: redis-server --save ""  # No persistence

  rabbitmq-test:
    image: rabbitmq:3.13-alpine
```

### 3.1.3 Quality Gates

| Gate | Criteria | Threshold |
|------|----------|-----------|
| Unit Test Coverage | Line coverage | ≥ 80% |
| Integration Tests | Pass rate | 100% |
| E2E Tests | Pass rate | ≥ 95% |
| Performance | P99 latency | < 500ms |
| Security Scan | Critical/High vulns | 0 |
| API Contract | Schema compliance | 100% |

### Checklist - Phase 3.1

- [ ] Create integration test directory structure
- [ ] Implement auth flow integration tests
- [ ] Implement portfolio operations tests
- [ ] Implement cross-service communication tests
- [ ] Set up test database fixtures
- [ ] Create docker-compose.test.yml
- [ ] Implement Locust load testing scripts
- [ ] Run security vulnerability scans
- [ ] Generate test coverage reports
- [ ] Document test execution procedures

---

## Phase 3.2: Shadow Mode Deployment

### 3.2.1 Shadow Mode Architecture

Shadow mode runs microservices in parallel with Django, comparing responses without affecting production traffic.

```
                    ┌──────────────────┐
                    │  Incoming Request │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   Traefik Router  │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │  Django (Primary)│          │  Microservices  │
    │  Returns Response│          │  (Shadow Copy)  │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             │    ┌─────────────────┐     │
             └───►│ Shadow Comparator│◄───┘
                  │  (Async Logger)  │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │  Comparison DB   │
                  │  + Dashboards    │
                  └─────────────────┘
```

### 3.2.2 Shadow Mode Configuration

```yaml
# traefik/shadow-mode.yml
http:
  routers:
    # Primary route to Django
    primary:
      rule: "PathPrefix(`/api/v1`)"
      service: django-primary
      middlewares:
        - shadow-mirror

  middlewares:
    shadow-mirror:
      mirroring:
        service: django-primary
        mirrors:
          - name: microservices-shadow
            percent: 100  # Mirror 100% of traffic

  services:
    django-primary:
      loadBalancer:
        servers:
          - url: "http://django-monolith:8000"

    microservices-shadow:
      loadBalancer:
        servers:
          - url: "http://shadow-comparator:9000"
```

### 3.2.3 Shadow Comparator Service

```python
# shadow-comparator/app/main.py
"""
Shadow Comparator Service
Receives mirrored requests, calls microservices, compares with Django response
"""

from fastapi import FastAPI, Request
import httpx
import json
from datetime import datetime

app = FastAPI(title="Shadow Comparator")

ENDPOINT_MAPPING = {
    "/api/v1/auth/login": ("auth-service:8007", "/api/v2/auth/login"),
    "/api/v1/stocks/": ("stock-data-service:8001", "/api/v2/stocks/"),
    "/api/v1/portfolio/": ("portfolio-service:8003", "/api/v2/portfolio/"),
    # ... more mappings
}

@app.post("/compare")
async def compare_response(request: Request):
    """Compare Django response with microservice response"""
    body = await request.json()

    original_path = body["original_path"]
    django_response = body["django_response"]

    # Get microservice mapping
    service, new_path = map_endpoint(original_path)

    # Call microservice
    async with httpx.AsyncClient() as client:
        ms_response = await client.request(
            method=body["method"],
            url=f"http://{service}{new_path}",
            headers=body["headers"],
            json=body.get("body")
        )

    # Compare and log
    comparison = compare_responses(django_response, ms_response.json())
    await log_comparison(original_path, comparison)

    return {"status": "logged", "match": comparison["match"]}
```

### 3.2.4 Comparison Metrics Dashboard

**Key Metrics to Track**:

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Response Match Rate | % of identical responses | < 95% |
| Latency Difference | ms difference | > 100ms |
| Error Rate Difference | % difference in errors | > 1% |
| Data Consistency | % of matching data fields | < 99% |
| Schema Compliance | API schema match | < 100% |

### Checklist - Phase 3.2

- [ ] Create shadow comparator service
- [ ] Configure Traefik mirroring
- [ ] Set up comparison database (ClickHouse/TimescaleDB)
- [ ] Create endpoint mapping configuration
- [ ] Build comparison dashboard in Grafana
- [ ] Implement response diff algorithm
- [ ] Set up alerting for discrepancies
- [ ] Run shadow mode for minimum 1 week
- [ ] Analyze and fix discrepancies
- [ ] Document shadow mode findings

---

## Phase 3.3: Data Migration

### 3.3.1 Database Schema Mapping

```
┌─────────────────────────────────────────────────────────────────┐
│                    DJANGO MONOLITH                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    defaultdb                              │  │
│  │  - auth_user              - stock_company                 │  │
│  │  - stock_portfolio        - stock_holding                 │  │
│  │  - stock_transaction      - stock_pricealert              │  │
│  │  - ml_model               - ml_prediction                 │  │
│  │  - analysis_report        - ai_insight                    │  │
│  │  - chat_session           - chat_message                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MIGRATION
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MICROSERVICES                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   auth_db   │  │ stockdata_db│  │ portfolio_db│              │
│  │  - users    │  │  - companies│  │  - portfolios│             │
│  │  - tokens   │  │  - prices   │  │  - holdings  │             │
│  │  - sessions │  │  - indices  │  │  - alerts    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │prediction_db│  │ analysis_db │  │  (Redis)    │              │
│  │  - models   │  │  - reports  │  │  - sessions │              │
│  │  - results  │  │  - screeners│  │  - cache    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3.2 Migration Scripts

```
migrations/
├── scripts/
│   ├── 001_migrate_users.py           # User accounts
│   ├── 002_migrate_companies.py       # Company data
│   ├── 003_migrate_portfolios.py      # Portfolio + holdings
│   ├── 004_migrate_transactions.py    # Transaction history
│   ├── 005_migrate_alerts.py          # Price alerts
│   ├── 006_migrate_models.py          # ML models
│   ├── 007_migrate_predictions.py     # Prediction history
│   └── 008_verify_migration.py        # Verification script
├── rollback/
│   └── rollback_all.py                # Emergency rollback
└── sync/
    ├── sync_users.py                  # Continuous sync
    └── sync_portfolios.py             # Real-time sync
```

### 3.3.3 Migration Strategy

**Phase A: Initial Data Load**
```python
# migrations/scripts/001_migrate_users.py
"""Migrate users from Django to auth-service"""

import asyncio
from sqlalchemy import create_engine, text
from datetime import datetime

DJANGO_DB = "mysql+pymysql://user:pass@host/defaultdb"
AUTH_DB = "mysql+pymysql://user:pass@host/auth_db"

async def migrate_users():
    """Migrate user accounts with password hashes"""

    source = create_engine(DJANGO_DB)
    target = create_engine(AUTH_DB)

    # Read from Django
    with source.connect() as conn:
        users = conn.execute(text("""
            SELECT id, username, email, password,
                   first_name, last_name, is_active,
                   date_joined, last_login
            FROM auth_user
            WHERE is_active = 1
        """)).fetchall()

    # Transform and load
    with target.connect() as conn:
        for user in users:
            conn.execute(text("""
                INSERT INTO users (
                    legacy_id, username, email, password_hash,
                    first_name, last_name, is_active,
                    created_at, last_login_at
                ) VALUES (
                    :id, :username, :email, :password,
                    :first_name, :last_name, :is_active,
                    :date_joined, :last_login
                )
                ON DUPLICATE KEY UPDATE
                    last_login_at = VALUES(last_login_at)
            """), dict(user._mapping))
        conn.commit()

    print(f"Migrated {len(users)} users")
```

**Phase B: Continuous Sync (During Shadow Mode)**
```python
# migrations/sync/sync_portfolios.py
"""Real-time portfolio sync using RabbitMQ"""

import aio_pika
from sqlalchemy.ext.asyncio import create_async_engine

async def start_sync():
    """Listen for Django changes and sync to microservices"""

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    queue = await channel.declare_queue("django.portfolio.changes")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                change = json.loads(message.body)
                await sync_change(change)

async def sync_change(change: dict):
    """Sync individual change to portfolio-service DB"""
    if change["action"] == "create":
        await create_portfolio(change["data"])
    elif change["action"] == "update":
        await update_portfolio(change["data"])
    elif change["action"] == "delete":
        await delete_portfolio(change["id"])
```

### 3.3.4 Data Verification

```python
# migrations/scripts/008_verify_migration.py
"""Verify data migration completeness and accuracy"""

async def verify_migration():
    """Compare record counts and sample data"""

    results = {}

    # User count
    django_users = await count_django_table("auth_user")
    ms_users = await count_ms_table("auth_db", "users")
    results["users"] = {
        "django": django_users,
        "microservice": ms_users,
        "match": django_users == ms_users
    }

    # Portfolio count
    django_portfolios = await count_django_table("stock_portfolio")
    ms_portfolios = await count_ms_table("portfolio_db", "portfolios")
    results["portfolios"] = {
        "django": django_portfolios,
        "microservice": ms_portfolios,
        "match": django_portfolios == ms_portfolios
    }

    # Sample data verification
    results["sample_verification"] = await verify_sample_records()

    return results
```

### Checklist - Phase 3.3

- [ ] Document current Django schema
- [ ] Design microservice database schemas
- [ ] Create user migration script
- [ ] Create portfolio migration script
- [ ] Create transaction history migration
- [ ] Set up continuous sync mechanism
- [ ] Implement data verification scripts
- [ ] Test migration on staging environment
- [ ] Create rollback procedures
- [ ] Execute production migration
- [ ] Verify migration completeness

---

## Phase 3.4: Gradual Traffic Cutover

### 3.4.1 Traffic Splitting Strategy

```
Week 1:  Django 100% │ Microservices 0%   (Shadow only)
Week 2:  Django 90%  │ Microservices 10%  (Canary)
Week 3:  Django 70%  │ Microservices 30%  (Early adopters)
Week 4:  Django 50%  │ Microservices 50%  (50/50 split)
Week 5:  Django 20%  │ Microservices 80%  (Majority migrated)
Week 6:  Django 5%   │ Microservices 95%  (Final validation)
Week 7:  Django 0%   │ Microservices 100% (Complete cutover)
```

### 3.4.2 Feature Flag Configuration

```yaml
# config/feature-flags.yml
feature_flags:
  # Service-level flags
  auth_microservice:
    enabled: true
    percentage: 100
    user_whitelist: []

  stock_data_microservice:
    enabled: true
    percentage: 100

  portfolio_microservice:
    enabled: true
    percentage: 50
    user_whitelist:
      - "beta_testers"
      - "internal_users"

  prediction_microservice:
    enabled: true
    percentage: 30

  analysis_microservice:
    enabled: true
    percentage: 30

  ai_insights_microservice:
    enabled: true
    percentage: 20

  chatbot_microservice:
    enabled: true
    percentage: 20

  # Endpoint-level flags
  endpoints:
    "/api/v2/portfolio/summary":
      enabled: true
      percentage: 100
    "/api/v2/predictions/train":
      enabled: true
      percentage: 50
      require_feature: "ml_v2"
```

### 3.4.3 Traefik Weighted Routing

```yaml
# traefik/weighted-routing.yml
http:
  routers:
    portfolio-weighted:
      rule: "PathPrefix(`/api/v2/portfolio`)"
      service: portfolio-weighted
      middlewares:
        - feature-check

  services:
    portfolio-weighted:
      weighted:
        services:
          - name: portfolio-microservice
            weight: 50
          - name: django-portfolio
            weight: 50
        healthCheck:
          path: /health/live
          interval: 5s

    portfolio-microservice:
      loadBalancer:
        servers:
          - url: "http://portfolio-service:8003"

    django-portfolio:
      loadBalancer:
        servers:
          - url: "http://django-monolith:8000"
```

### 3.4.4 Rollback Procedures

```bash
#!/bin/bash
# scripts/rollback.sh
# Emergency rollback to Django monolith

set -e

ENVIRONMENT=${1:-staging}

echo "=== EMERGENCY ROLLBACK INITIATED ==="
echo "Environment: $ENVIRONMENT"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 1. Update Traefik routing to 100% Django
echo "Switching all traffic to Django..."
kubectl apply -f traefik/rollback-config.yml

# 2. Disable microservices feature flags
echo "Disabling microservice feature flags..."
curl -X POST http://feature-service/api/flags/disable-all-microservices

# 3. Scale down microservices (keep running for debugging)
echo "Scaling down microservices..."
kubectl scale deployment --all --replicas=1 -n microservices

# 4. Alert on-call team
echo "Sending alerts..."
curl -X POST http://alertmanager/api/v1/alerts \
  -d '{"labels":{"severity":"critical","type":"rollback"}}'

# 5. Log rollback event
echo "Logging rollback event..."
curl -X POST http://audit-log/api/events \
  -d '{"event":"emergency_rollback","environment":"'$ENVIRONMENT'"}'

echo "=== ROLLBACK COMPLETE ==="
echo "Django is now serving 100% of traffic"
echo "Microservices are scaled down but running for debugging"
```

### 3.4.5 Cutover Metrics & Alerts

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Error Rate | > 1% | > 5% | Reduce traffic % |
| P99 Latency | > 300ms | > 500ms | Investigate |
| Success Rate | < 99% | < 95% | Rollback |
| Data Consistency | < 99.5% | < 99% | Pause migration |

### Checklist - Phase 3.4

- [ ] Configure feature flag service
- [ ] Set up Traefik weighted routing
- [ ] Create rollback scripts
- [ ] Define cutover metrics and thresholds
- [ ] Set up real-time monitoring dashboard
- [ ] Configure alerting rules
- [ ] Train support team on new architecture
- [ ] Execute Week 1 (shadow mode)
- [ ] Execute Week 2-3 (canary release)
- [ ] Execute Week 4-5 (majority cutover)
- [ ] Execute Week 6-7 (complete migration)
- [ ] Decommission Django endpoints

---

## Phase 3.5: Production Hardening

### 3.5.1 Security Audit Checklist

**Authentication & Authorization**:
- [ ] JWT token validation on all protected endpoints
- [ ] Token expiration and refresh working correctly
- [ ] Role-based access control (RBAC) implemented
- [ ] Session invalidation on logout
- [ ] Brute force protection on login
- [ ] Password complexity requirements enforced

**API Security**:
- [ ] Input validation on all endpoints
- [ ] SQL injection protection (parameterized queries)
- [ ] XSS protection (output encoding)
- [ ] CSRF protection for state-changing operations
- [ ] Rate limiting configured and tested
- [ ] Request size limits set

**Infrastructure Security**:
- [ ] TLS 1.3 for all external traffic
- [ ] Internal service mesh encryption (mTLS)
- [ ] Secrets management (no hardcoded credentials)
- [ ] Network policies restricting inter-service communication
- [ ] Container security scanning
- [ ] Dependency vulnerability scanning

**Data Security**:
- [ ] PII data encryption at rest
- [ ] Sensitive data masking in logs
- [ ] Database connection encryption
- [ ] Backup encryption
- [ ] Data retention policies implemented

### 3.5.2 Performance Optimization

```yaml
# Performance Targets
targets:
  api_latency:
    p50: 50ms
    p95: 150ms
    p99: 300ms

  throughput:
    auth: 1000 req/s
    stock_data: 500 req/s
    portfolio: 200 req/s

  availability:
    target: 99.9%
    max_downtime_monthly: 43.8 minutes
```

**Optimization Areas**:

| Area | Optimization | Impact |
|------|--------------|--------|
| Database | Connection pooling, query optimization, indexes | 30-50% latency reduction |
| Caching | Redis for hot data, response caching | 60-80% hit rate |
| API | Response compression, pagination, field filtering | 40% bandwidth reduction |
| Compute | Container resource limits, auto-scaling | Cost optimization |

### 3.5.3 High Availability Configuration

```yaml
# kubernetes/deployment-ha.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: portfolio-service
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                topologyKey: kubernetes.io/hostname
      containers:
        - name: portfolio-service
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8003
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8003
            initialDelaySeconds: 5
            periodSeconds: 5
```

### 3.5.4 Disaster Recovery

```yaml
# Disaster Recovery Plan
rpo: 1 hour    # Recovery Point Objective
rto: 4 hours   # Recovery Time Objective

backup_strategy:
  database:
    type: automated
    frequency: hourly
    retention: 30 days
    location: s3://backups/mysql/

  redis:
    type: rdb_snapshot
    frequency: every_5_minutes

  configuration:
    type: git
    repository: github.com/org/stock-helper-config

recovery_procedures:
  database_failure:
    1: failover_to_replica
    2: restore_from_backup
    3: replay_wal_logs

  complete_outage:
    1: deploy_to_dr_region
    2: restore_databases
    3: update_dns
    4: verify_functionality
```

### Checklist - Phase 3.5

- [ ] Complete security audit
- [ ] Fix all critical/high vulnerabilities
- [ ] Implement rate limiting per user/IP
- [ ] Configure TLS certificates
- [ ] Set up secrets management (Vault/AWS Secrets)
- [ ] Optimize database queries (slow query log analysis)
- [ ] Configure Redis caching strategy
- [ ] Implement response compression
- [ ] Configure auto-scaling policies
- [ ] Set up multi-replica deployments
- [ ] Configure pod anti-affinity
- [ ] Test failover scenarios
- [ ] Document disaster recovery procedures
- [ ] Run DR drill

---

## Phase 3.6: Django Decommissioning

### 3.6.1 Decommission Checklist

- [ ] Confirm 100% traffic on microservices for 2+ weeks
- [ ] Verify no direct Django database connections
- [ ] Archive Django codebase
- [ ] Export and archive Django logs
- [ ] Remove Django from docker-compose
- [ ] Clean up Django-specific infrastructure
- [ ] Update documentation
- [ ] Notify stakeholders of completion

### 3.6.2 Post-Migration Cleanup

```bash
# Remove legacy routes from Traefik
# Remove Django service from docker-compose
# Archive Django database (keep for 90 days)
# Update CI/CD pipelines
# Remove Django dependencies from requirements
```

---

## Success Criteria

### Phase 3.1 - Integration Testing
- [ ] 100% integration test pass rate
- [ ] ≥80% code coverage
- [ ] Zero critical security vulnerabilities
- [ ] Performance benchmarks documented

### Phase 3.2 - Shadow Mode
- [ ] ≥95% response match rate
- [ ] Shadow mode running for 1+ week
- [ ] All discrepancies investigated and resolved

### Phase 3.3 - Data Migration
- [ ] 100% data migrated
- [ ] Zero data loss
- [ ] Data verification scripts pass

### Phase 3.4 - Traffic Cutover
- [ ] 100% traffic on microservices
- [ ] Zero rollbacks in final week
- [ ] SLA maintained throughout

### Phase 3.5 - Production Hardening
- [ ] Security audit passed
- [ ] Performance targets met
- [ ] HA configuration validated
- [ ] DR procedures tested

### Phase 3.6 - Decommissioning
- [ ] Django fully decommissioned
- [ ] Documentation updated
- [ ] Team trained on new architecture

---

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1-2 | 3.1 | Integration test suite complete |
| 3 | 3.2 | Shadow mode deployed |
| 4 | 3.3 | Data migration complete |
| 5-6 | 3.4 | Gradual cutover (10% → 50%) |
| 7-8 | 3.4 | Complete cutover (100%) |
| 9 | 3.5 | Production hardening |
| 10 | 3.6 | Django decommissioning |

---

## Appendix

### A. Useful Commands

```bash
# Check service health
curl http://localhost:8007/health/ready  # auth-service
curl http://localhost:8001/health/ready  # stock-data-service
curl http://localhost:8003/health/ready  # portfolio-service

# View logs
docker-compose logs -f auth-service
docker-compose logs -f --tail=100 portfolio-service

# Run integration tests
docker-compose -f docker-compose.test.yml up --build

# Check Traefik routing
curl http://localhost:8080/api/http/routers

# Monitor RabbitMQ queues
curl -u stockuser:stockpass http://localhost:15672/api/queues
```

### B. Contact Points

| Role | Responsibility |
|------|----------------|
| Tech Lead | Architecture decisions, escalations |
| DevOps | Infrastructure, deployment |
| QA Lead | Testing, quality gates |
| Security | Security audit, compliance |
| DBA | Database migration, performance |

### C. Related Documents

- PHASE2_IMPLEMENTATION_PLAN.md
- stock-common/README.md
- monitoring/grafana/dashboards/
- traefik/dynamic.yml

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Author: Claude Code Assistant*
