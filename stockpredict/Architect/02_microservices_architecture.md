# 02 — Microservices Architecture

## 2.1 Service Dependency Map

```mermaid
graph TD
    subgraph INFRA["Infrastructure"]
        MYSQL[("MySQL 8")]
        REDIS[("Redis")]
        MQ[("RabbitMQ")]
        NEO4J[("Neo4j")]
    end

    subgraph EXTERNAL["External APIs"]
        VNSTOCK["VNStock/VCI"]
        OPENAI["OpenAI"]
        CLAUDE["Anthropic"]
        OLLAMA["Ollama"]
    end

    AUTH["🔐 auth-service\n:8007\nJWT · Users · Roles"]
    STOCK["📈 stock-data-service\n:8001\nPrices · Companies · Market"]
    PORT["💼 portfolio-service\n:8003\nPortfolios · Holdings · Alerts"]
    PRED["🤖 prediction-service\n:8002\nML Models · Predictions · Backtest"]
    ANAL["📊 analysis-service\n:8004\nTA · FA · Screener"]
    AI["💡 ai-insights-service\n:8005\nLLM Insights · Sentiment"]
    CHAT["💬 chatbot-service\n:8006\nConversational AI"]
    JOUR["📔 journal-service\n:8008\nTrade Journal · Risk"]
    QA["🧠 knowledge-qa-service\n:8009\nGraph RAG · Q&A"]

    %% DB connections
    AUTH --> MYSQL
    STOCK --> MYSQL
    PORT --> MYSQL
    PRED --> MYSQL
    ANAL --> MYSQL
    JOUR --> MYSQL
    QA --> NEO4J

    %% Cache connections
    AI --> REDIS
    CHAT --> REDIS
    STOCK --> REDIS
    PORT --> REDIS

    %% Event bus
    STOCK -->|"stock.price.updated\nstock.company.synced"| MQ
    PRED -->|"prediction.training.*\nprediction.generated"| MQ
    PORT -->|"portfolio.updated\nalert.triggered"| MQ
    ANAL -->|"analysis.completed"| MQ

    %% Inter-service HTTP calls
    CHAT -->|"GET /companies\nGET /stocks"| STOCK
    CHAT -->|"GET /analysis"| ANAL
    CHAT -->|"GET /predict"| PRED
    CHAT -->|"GET /ai/insight"| AI
    AI -->|"GET /stocks (price data)"| STOCK
    AI -->|"GET /analysis (signals)"| ANAL
    PORT -->|"GET /stocks (prices)"| STOCK

    %% External
    STOCK --> VNSTOCK
    AI --> OPENAI
    AI --> CLAUDE
    QA --> OLLAMA

    %% MQ consumers
    MQ -->|"stock.price.updated"| PORT
    MQ -->|"stock.data.available"| PRED

    style AUTH fill:#fef9c3,stroke:#ca8a04
    style STOCK fill:#dbeafe,stroke:#3b82f6
    style PORT fill:#dcfce7,stroke:#16a34a
    style PRED fill:#f3e8ff,stroke:#9333ea
    style ANAL fill:#e0f2fe,stroke:#0284c7
    style AI fill:#fff7ed,stroke:#ea580c
    style CHAT fill:#fce7f3,stroke:#db2777
    style JOUR fill:#f0fdf4,stroke:#15803d
    style QA fill:#fdf4ff,stroke:#c026d3
```

---

## 2.2 Service Internal Architecture (Standard Pattern)

Every service follows the same layered structure:

```mermaid
graph TD
    subgraph SERVICE["Microservice (e.g. stock-data-service)"]
        subgraph HTTP["HTTP Layer"]
            ROUTES["api/routes.py\nFastAPI Router\nPydantic schemas\n(request / response)"]
            HEALTH["/health/live\n/health/ready\n/metrics"]
        end

        subgraph BIZ["Business Logic Layer"]
            SVC["services/\nDomain Services\nbusiness rules\norchestration"]
        end

        subgraph REPO["Data Access Layer"]
            REPOS["repositories/\nBaseRepository\nCRUD + queries\nasync SQLAlchemy"]
        end

        subgraph MODEL["Domain Model Layer"]
            DOM["models/domain.py\nSQLAlchemy ORM entities"]
            SCHEMA["models/schemas.py\nPydantic DTOs"]
        end

        subgraph INFRA["Infrastructure"]
            CONF["config.py\npydantic-settings\nenv vars"]
            MAIN["main.py\nFastAPI app\nlifespan hooks\nmiddleware"]
        end
    end

    ROUTES --> SVC
    SVC --> REPOS
    REPOS --> DOM
    ROUTES --> SCHEMA
    MAIN --> ROUTES
    MAIN --> HEALTH
    CONF --> MAIN

    DB[("MySQL")]
    CACHE[("Redis")]
    MQ[("RabbitMQ")]

    REPOS --> DB
    SVC --> CACHE
    SVC --> MQ

    COMMON["stock-common\nlibrary"]
    MAIN --> COMMON
    REPOS --> COMMON

    style HTTP fill:#dbeafe
    style BIZ fill:#dcfce7
    style REPO fill:#fef9c3
    style MODEL fill:#f3e8ff
    style INFRA fill:#fee2e2
```

---

## 2.3 Service Responsibility Matrix

```mermaid
mindmap
  root((Stock Predict\nPlatform))
    Identity & Access
      auth-service
        User registration / login
        JWT issuance & refresh
        Password management
        Role management
    Market Data
      stock-data-service
        Stock price history
        Company profiles
        VN30 price board
        Market indices
        Background data sync
    Portfolio
      portfolio-service
        Portfolio CRUD
        Holdings tracking
        Transaction history
        Price alerts
        Watchlists
    Intelligence
      prediction-service
        ML model registry
        Model training & versioning
        Price predictions
        Backtesting engine
        Simulation
      analysis-service
        Technical indicators RSI MACD BB
        Fundamental analysis
        Financial statements
        Stock screener
        Pattern detection
      ai-insights-service
        LLM market summaries
        Sentiment analysis
        Stock comparison
        Sector analysis
        News analysis
    Conversational AI
      chatbot-service
        Natural language queries
        Chat history
        Capability routing
        Feedback collection
      knowledge-qa-service
        Graph RAG
        Knowledge base Q&A
        Note search
        Graph statistics
    Journaling
      journal-service
        Account management
        Trade diary
        Daily/weekly plans
        Risk metrics
        Equity snapshots
```

---

## 2.4 Inter-Service Communication Patterns

```mermaid
flowchart LR
    subgraph SYNC["Synchronous (HTTP/REST)"]
        direction TB
        S1["chatbot-service\n→ stock-data-service\n(get company info)"]
        S2["chatbot-service\n→ analysis-service\n(get technicals)"]
        S3["chatbot-service\n→ ai-insights-service\n(get LLM insight)"]
        S4["ai-insights-service\n→ stock-data-service\n(get price data)"]
        S5["portfolio-service\n→ stock-data-service\n(get current prices)"]
    end

    subgraph ASYNC["Asynchronous (RabbitMQ Events)"]
        direction TB
        A1["stock-data-service\n──PUBLISH──▶\nstock.price.updated\nstock.company.synced"]
        A2["prediction-service\n──PUBLISH──▶\nprediction.training.completed\nprediction.generated"]
        A3["portfolio-service\n──PUBLISH──▶\nportfolio.updated\nalert.triggered"]
        A4["──SUBSCRIBE──▶\nportfolio-service\n(stock price changes)"]
        A5["──SUBSCRIBE──▶\nprediction-service\n(new data available)"]
    end

    A1 --> A4
    A1 --> A5

    style SYNC fill:#dbeafe,stroke:#3b82f6
    style ASYNC fill:#dcfce7,stroke:#22c55e
```

---

## 2.5 Knowledge-QA Service — Special Architecture

This service uses full DDD layering, unlike the simpler CRUD services:

```mermaid
flowchart TD
    API["API Layer\nknowledge_qa_router.py\nFastAPI endpoints"] 
    
    subgraph APP["Application Layer"]
        UC_ASK["AskQuestion\nUseCase"]
        UC_HIST["GetChatHistory\nUseCase"]
        UC_SRCH["SearchNotes\nUseCase"]
        UC_STAT["GetGraphStats\nUseCase"]
        CMD["Commands"]
        QRY["Queries"]
        DTO["DTOs / Mappers"]
    end

    subgraph DOMAIN["Domain Layer"]
        ENT["Entities\nChatMessage\nChatSession\nKnowledgeNote"]
        VO["Value Objects\nSearchQuery\nGraphContext\nLLMResponse\nNoteReference"]
        PORTS["Ports (Interfaces)\nLLMPort\nKnowledgeGraphRepository\nChatSessionRepository"]
        DOM_SVC["Domain Services\nQueryUnderstanding\nGraphRetrieval\nAnswerGeneration"]
    end

    subgraph INFRA["Infrastructure Layer"]
        NEO4J_REPO["Neo4jKnowledgeGraphRepository\n(implements KnowledgeGraphPort)"]
        MEM_REPO["InMemorySessionRepository\n(implements ChatSessionPort)"]
        OLLAMA["OllamaAdapter\n(implements LLMPort)"]
        PROMPT["PromptBuilder"]
        FACTORY["GraphContextFactory"]
    end

    subgraph EXTERNAL["External"]
        NEO4J_DB[("Neo4j\nGraph DB")]
        OLLAMA_SVC["Ollama\nLocal LLM"]
    end

    API --> UC_ASK & UC_HIST & UC_SRCH & UC_STAT
    UC_ASK --> CMD & DOM_SVC
    UC_HIST --> QRY
    UC_SRCH --> QRY
    DOM_SVC --> PORTS
    PORTS -->|"impl"| NEO4J_REPO & MEM_REPO & OLLAMA
    NEO4J_REPO --> NEO4J_DB
    OLLAMA --> OLLAMA_SVC
    DOM_SVC --> VO & ENT

    style APP fill:#dbeafe
    style DOMAIN fill:#dcfce7
    style INFRA fill:#fef9c3
    style EXTERNAL fill:#fee2e2
```
