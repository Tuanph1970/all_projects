# Stock Predict Platform — Architecture Documentation

> Generated: 2026-05-07 | Source: live codebase analysis

## Documents in this folder

| # | File | What it covers |
|---|------|---------------|
| 01 | [System Overview Pipeline](01_system_overview.md) | End-to-end request flow, C4 context & container diagrams |
| 02 | [Microservices Architecture](02_microservices_architecture.md) | All 9 services, inter-service calls, dependencies |
| 03 | [API Gateway & Routing](03_api_gateway_routing.md) | Traefik routing table, path rules, middleware |
| 04 | [Domain Models & Class Diagrams](04_domain_models_class_diagrams.md) | SQLAlchemy entities per service, relationships |
| 05 | [Event-Driven Architecture](05_event_driven_architecture.md) | RabbitMQ event bus, pub/sub topology, DLQ |
| 06 | [DDD & Design Patterns](06_ddd_design_patterns.md) | DDD layers, CQRS, Repository, Factory patterns |
| 07 | [Frontend Architecture](07_frontend_architecture.md) | React component tree, service layer, state management |
| 08 | [Data Architecture](08_data_architecture.md) | MySQL schema overview, Redis caching, Neo4j graph |
| 09 | [Resilience Patterns](09_resilience_patterns.md) | Circuit breaker, retry, bulkhead, timeout |
| 10 | [Deployment & Infrastructure](10_deployment_infrastructure.md) | Docker Compose topology, ports, profiles, CI/CD |
| 11 | [Knowledge-QA Deep Dive](11_knowledge_qa_ddd.md) | Full DDD + Graph RAG architecture |
| 12 | [Auth & Security Flow](12_auth_security_flow.md) | JWT lifecycle, auth middleware, shared secret |

## Technology Radar

```
Backend  : Python 3.11 · FastAPI · SQLAlchemy (async) · Pydantic v2
Database : MySQL 8 · Redis 7 · Neo4j (Graph RAG)
Messaging: RabbitMQ 3 (aio-pika, topic exchange)
AI / ML  : OpenAI · Anthropic Claude · Ollama (local LLM)
Gateway  : Traefik v2
Frontend : React 19 · CRA · Fetch API · Context API
Observ.  : Prometheus · Grafana · Jaeger (OTLP) · structlog
Infra    : Docker Compose · GitHub Actions CI
```
