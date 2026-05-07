# 01 — System Overview Pipeline

## 1.1 C4 Context Diagram — Who uses the system

```mermaid
C4Context
  title Stock Predict Platform — System Context

  Person(trader, "Retail Trader", "Uses web app for market analysis, portfolio management, AI-powered insights")
  Person(admin, "Admin", "Manages users, monitors system health")

  System(stockpredict, "Stock Predict Platform", "Vietnamese stock market analysis, prediction, and AI advisory platform")

  System_Ext(vnstock, "VNStock / VCI Data Feed", "Real-time Vietnamese stock price & company data")
  System_Ext(openai, "OpenAI API", "GPT-4 for AI insights and chat")
  System_Ext(anthropic, "Anthropic Claude API", "Claude for AI analysis")
  System_Ext(mysql_remote, "Remote MySQL DB", "SSH-tunnelled production database")
  System_Ext(neo4j, "Neo4j Graph DB", "Knowledge graph for RAG")
  System_Ext(ollama, "Ollama (local LLM)", "Local inference for knowledge QA")

  Rel(trader, stockpredict, "Uses", "HTTPS / Browser")
  Rel(admin, stockpredict, "Manages", "HTTPS / Browser")

  Rel(stockpredict, vnstock, "Pulls stock prices & company data", "Python SDK")
  Rel(stockpredict, openai, "Calls for AI insights", "REST / HTTPS")
  Rel(stockpredict, anthropic, "Calls for AI analysis", "REST / HTTPS")
  Rel(stockpredict, mysql_remote, "Reads/writes business data", "TCP 3306 via SSH tunnel")
  Rel(stockpredict, neo4j, "Graph queries for RAG", "Bolt 7687")
  Rel(stockpredict, ollama, "Local LLM inference", "REST 11434")
```

---

## 1.2 C4 Container Diagram — Internal architecture

```mermaid
C4Container
  title Stock Predict Platform — Containers

  Person(user, "User / Trader")

  Container(frontend, "React SPA", "React 19 / CRA", "Single-page app; all API calls via Fetch through Traefik gateway")

  Container(traefik, "Traefik API Gateway", "Traefik v2", "Path-prefix routing, TLS termination, load balancing, auth middleware")

  Container(auth_svc, "auth-service :8007", "FastAPI", "JWT issuing, user registration, password management")
  Container(stock_svc, "stock-data-service :8001", "FastAPI", "Company data, stock prices, VN30 priceboard, market info")
  Container(portfolio_svc, "portfolio-service :8003", "FastAPI", "Portfolios, holdings, transactions, watchlists, alerts")
  Container(pred_svc, "prediction-service :8002", "FastAPI + ML", "ML model management, predictions, backtesting, simulation")
  Container(analysis_svc, "analysis-service :8004", "FastAPI + TA-Lib", "Technical & fundamental analysis, screener")
  Container(ai_svc, "ai-insights-service :8005", "FastAPI + LLM", "AI-generated market insights via OpenAI / Claude")
  Container(chat_svc, "chatbot-service :8006", "FastAPI + LLM", "Conversational AI for stock queries")
  Container(journal_svc, "journal-service :8008", "FastAPI", "Trading journal, plans, risk metrics")
  Container(qa_svc, "knowledge-qa-service :8009", "FastAPI + GraphRAG", "Knowledge base Q&A via Neo4j + Ollama")

  ContainerDb(mysql, "MySQL 8", "Relational DB", "Primary system of record for all services")
  ContainerDb(redis, "Redis 7", "Cache", "Session cache, API response cache, rate limiting")
  ContainerDb(rabbitmq, "RabbitMQ 3", "Message Broker", "Async event bus with topic exchange")
  ContainerDb(neo4j_db, "Neo4j", "Graph DB", "Knowledge graph for RAG queries")

  Container(prometheus, "Prometheus", "Metrics", "Scrapes /metrics from all services")
  Container(grafana, "Grafana :3100", "Dashboards", "Visualises Prometheus metrics")
  Container(jaeger, "Jaeger :16686", "Tracing", "Distributed trace collection via OTLP")

  Rel(user, frontend, "Uses", "HTTPS :3004")
  Rel(frontend, traefik, "API calls", "HTTP :8004")

  Rel(traefik, auth_svc, "/auth/*")
  Rel(traefik, stock_svc, "/companies|stocks|market|industries|priceboards/*")
  Rel(traefik, portfolio_svc, "/portfolio/*")
  Rel(traefik, pred_svc, "/predictions|predict|models|solutions/*")
  Rel(traefik, analysis_svc, "/analysis/*")
  Rel(traefik, ai_svc, "/ai/*")
  Rel(traefik, chat_svc, "/chat/*")
  Rel(traefik, journal_svc, "/journal/*")
  Rel(traefik, qa_svc, "/knowledge-qa/*")

  Rel(auth_svc, mysql, "R/W users, tokens")
  Rel(stock_svc, mysql, "R/W stocks, companies")
  Rel(portfolio_svc, mysql, "R/W portfolios")
  Rel(pred_svc, mysql, "R/W models, predictions")
  Rel(analysis_svc, mysql, "R analysis data")
  Rel(journal_svc, mysql, "R/W journal entries")
  Rel(qa_svc, neo4j_db, "Graph queries")

  Rel(ai_svc, redis, "Cache insights")
  Rel(chat_svc, redis, "Cache chat sessions")
  Rel(portfolio_svc, rabbitmq, "Publishes portfolio events")
  Rel(pred_svc, rabbitmq, "Publishes prediction events")
  Rel(stock_svc, rabbitmq, "Publishes stock sync events")

  Rel(prometheus, auth_svc, "Scrape /metrics")
  Rel(prometheus, stock_svc, "Scrape /metrics")
  Rel(grafana, prometheus, "Query")
  Rel(jaeger, auth_svc, "Receive OTLP traces")
```

---

## 1.3 End-to-End Request Pipeline

```mermaid
flowchart TD
    subgraph CLIENT["🌐 Client Layer"]
        Browser["React SPA\n(localhost:3004)"]
    end

    subgraph GATEWAY["🔀 API Gateway — Traefik :8004"]
        TK_AUTH["Auth Middleware\n(JWT validation)"]
        TK_ROUTE["Path-Prefix Router"]
        TK_LB["Load Balancer\n(round-robin)"]
    end

    subgraph SERVICES["⚙️ Microservices Layer"]
        AUTH["auth-service\n:8007"]
        STOCK["stock-data-service\n:8001"]
        PORT["portfolio-service\n:8003"]
        PRED["prediction-service\n:8002"]
        ANAL["analysis-service\n:8004i"]
        AI["ai-insights-service\n:8005"]
        CHAT["chatbot-service\n:8006"]
        JOUR["journal-service\n:8008"]
        QA["knowledge-qa-service\n:8009"]
    end

    subgraph SHARED["📦 Shared Library (stock-common)"]
        AUTH_LIB["JWT Validator"]
        DB_LIB["Async SQLAlchemy"]
        EVT_LIB["EventBus (RabbitMQ)"]
        RES_LIB["Circuit Breaker / Retry"]
        OBS_LIB["Metrics / Traces / Logs"]
    end

    subgraph DATA["🗄️ Data Layer"]
        MYSQL["MySQL 8\n(primary DB)"]
        REDIS["Redis 7\n(cache)"]
        MQ["RabbitMQ\n(event bus)"]
        NEO4J["Neo4j\n(knowledge graph)"]
    end

    subgraph EXTERNAL["🌍 External Systems"]
        VNSTOCK["VNStock / VCI\n(market data)"]
        OPENAI["OpenAI API"]
        CLAUDE["Anthropic Claude API"]
        OLLAMA["Ollama\n(local LLM)"]
    end

    subgraph OBS["📊 Observability"]
        PROM["Prometheus\n:9090"]
        GRAF["Grafana\n:3100"]
        JAEGER["Jaeger\n:16686"]
    end

    Browser -->|"1. HTTP Request\n/stock_helper/api/v2/..."| TK_AUTH
    TK_AUTH -->|"2. Validate JWT\n(shared secret)"| TK_ROUTE
    TK_ROUTE -->|"3. Match path prefix"| TK_LB
    TK_LB -->|"4. Forward to service"| SERVICES

    AUTH <--> AUTH_LIB
    STOCK <--> DB_LIB
    PORT <--> EVT_LIB
    PRED <--> RES_LIB
    AI <--> OBS_LIB

    SERVICES -->|"5. DB queries"| MYSQL
    SERVICES -->|"5b. Cache R/W"| REDIS
    SERVICES -->|"5c. Async events"| MQ
    QA -->|"5d. Graph queries"| NEO4J

    STOCK -->|"6. Pull market data"| VNSTOCK
    AI -->|"6b. LLM calls"| OPENAI
    AI -->|"6c. LLM calls"| CLAUDE
    QA -->|"6d. Local inference"| OLLAMA

    SERVICES -->|"metrics"| PROM
    SERVICES -->|"traces (OTLP)"| JAEGER
    PROM --> GRAF

    style CLIENT fill:#dbeafe,stroke:#3b82f6
    style GATEWAY fill:#fef3c7,stroke:#f59e0b
    style SERVICES fill:#dcfce7,stroke:#22c55e
    style SHARED fill:#f3e8ff,stroke:#a855f7
    style DATA fill:#fee2e2,stroke:#ef4444
    style EXTERNAL fill:#e0f2fe,stroke:#0ea5e9
    style OBS fill:#fdf4ff,stroke:#d946ef
```

---

## 1.4 Typical User Journey — Stock Analysis Request

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant SPA as React SPA
    participant TK as Traefik Gateway
    participant AUTH as auth-service
    participant STOCK as stock-data-service
    participant ANAL as analysis-service
    participant AI as ai-insights-service
    participant REDIS as Redis Cache
    participant DB as MySQL
    participant OPENAI as OpenAI API

    User->>SPA: Open stock detail page (e.g. VNM)
    SPA->>TK: GET /stock_helper/api/v2/stocks/VNM\n[Authorization: Bearer <jwt>]
    TK->>TK: Validate JWT (shared secret)
    TK->>STOCK: Forward request
    STOCK->>REDIS: Check cache key "stock:VNM"
    alt Cache HIT
        REDIS-->>STOCK: Return cached data
    else Cache MISS
        STOCK->>DB: SELECT * FROM stocks WHERE symbol='VNM'
        DB-->>STOCK: Stock record
        STOCK->>REDIS: SET "stock:VNM" TTL=300s
    end
    STOCK-->>SPA: Stock data response

    SPA->>TK: GET /stock_helper/api/v2/analysis/technical/VNM
    TK->>ANAL: Forward request
    ANAL->>DB: Load historical price data
    ANAL->>ANAL: Calculate RSI, MACD, Bollinger Bands
    ANAL-->>SPA: Technical indicators

    SPA->>TK: GET /stock_helper/api/v2/ai/insight/VNM
    TK->>AI: Forward request
    AI->>REDIS: Check insight cache
    alt Cache MISS
        AI->>STOCK: Get recent prices (inter-service HTTP)
        AI->>ANAL: Get technical signals
        AI->>OPENAI: Generate insight prompt
        OPENAI-->>AI: AI-generated insight text
        AI->>REDIS: Cache insight (TTL=1800s)
    end
    AI-->>SPA: AI insight

    SPA->>User: Render combined stock analysis page
```
