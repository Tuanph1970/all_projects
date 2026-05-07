# 08 — Data Architecture

## 8.1 MySQL Schema Overview (All Services)

```mermaid
erDiagram
    %% Auth Service
    users {
        int id PK
        varchar username UK
        varchar email UK
        varchar hashed_password
        varchar role
        bool is_active
        bool is_verified
        datetime created_at
        datetime updated_at
    }
    refresh_tokens {
        int id PK
        int user_id FK
        varchar token UK
        datetime expires_at
        bool is_revoked
        datetime created_at
    }

    %% Stock Data Service
    companies {
        varchar symbol PK
        varchar name
        varchar name_en
        varchar exchange
        int industry_id FK
        float market_cap
        datetime listed_date
        datetime updated_at
    }
    industries {
        int id PK
        varchar name
        varchar name_en
        varchar sector
        varchar icb_code
    }
    stocks {
        int id PK
        varchar symbol FK
        float open_price
        float high_price
        float low_price
        float close_price
        float volume
        date trade_date
        varchar source
    }

    %% Portfolio Service
    portfolios {
        int id PK
        int user_id FK
        varchar name
        float initial_capital
        float cash_balance
        datetime created_at
    }
    holdings {
        int id PK
        int portfolio_id FK
        varchar symbol
        float quantity
        float avg_cost
        datetime last_updated
    }
    transactions {
        int id PK
        int portfolio_id FK
        varchar symbol
        varchar type
        float quantity
        float price
        float fee
        datetime trade_date
    }
    alerts {
        int id PK
        int user_id FK
        varchar symbol
        varchar alert_type
        float target_value
        bool is_active
        bool is_triggered
        datetime triggered_at
    }

    %% Prediction Service
    model_instances {
        int id PK
        varchar name
        varchar model_type
        varchar symbol
        varchar status
        float accuracy
        json hyperparameters
        varchar file_path
        datetime trained_at
    }
    prediction_results {
        int id PK
        int model_id FK
        varchar symbol
        int horizon_days
        float predicted_price
        float confidence
        json prediction_series
        datetime predicted_at
    }
    tbl_solutions {
        int id PK
        varchar name
        varchar description
        datetime created_at
    }

    %% Journal Service
    trading_accounts {
        int id PK
        int user_id FK
        varchar name
        varchar broker
        float initial_capital
        float current_balance
        datetime created_at
    }
    trades {
        int id PK
        int account_id FK
        varchar symbol
        varchar direction
        varchar status
        float entry_price
        float exit_price
        float stop_loss
        float take_profit
        float quantity
        float pnl
        float rr_ratio
        datetime entry_date
        datetime exit_date
    }
    equity_snapshots {
        int id PK
        int account_id FK
        date snapshot_date
        float equity
        float drawdown
        float drawdown_pct
    }

    users ||--o{ refresh_tokens : has
    users ||--o{ portfolios : owns
    users ||--o{ alerts : creates
    users ||--o{ trading_accounts : has
    industries ||--o{ companies : classifies
    companies ||--o{ stocks : has
    portfolios ||--o{ holdings : contains
    portfolios ||--o{ transactions : records
    model_instances ||--o{ prediction_results : produces
    trading_accounts ||--o{ trades : records
    trading_accounts ||--o{ equity_snapshots : tracks
```

---

## 8.2 Redis Caching Strategy

```mermaid
flowchart TD
    subgraph CACHE_KEYS["Cache Key Patterns"]
        K1["stock:{symbol}\nTTL: 300s (5 min)\nStock price data\n→ stock-data-service"]
        K2["company:{symbol}\nTTL: 3600s (1 hr)\nCompany profile data\n→ stock-data-service"]
        K3["ai:insight:{symbol}\nTTL: 1800s (30 min)\nLLM-generated insight\n→ ai-insights-service"]
        K4["ai:market-overview\nTTL: 900s (15 min)\nMarket summary\n→ ai-insights-service"]
        K5["chat:session:{id}\nTTL: 3600s (1 hr)\nChat history\n→ chatbot-service"]
        K6["analysis:technical:{symbol}:{date}\nTTL: 86400s (24 hr)\nTA indicators\n→ analysis-service"]
        K7["portfolio:value:{id}\nTTL: 60s (1 min)\nPortfolio total value\n→ portfolio-service"]
        K8["priceboard:vn30\nTTL: 5s\nLive VN30 board\n→ stock-data-service"]
    end

    subgraph PATTERN["Cache-Aside Pattern"]
        REQ["Request arrives"]
        CHECK{"Cache\nHIT?"}
        RETURN_CACHE["Return cached\nresponse"]
        FETCH_DB["Query DB /\nExternal API"]
        STORE["Store in Redis\nwith TTL"]
        RETURN_FRESH["Return fresh\nresponse"]

        REQ --> CHECK
        CHECK -->|"HIT"| RETURN_CACHE
        CHECK -->|"MISS"| FETCH_DB
        FETCH_DB --> STORE
        STORE --> RETURN_FRESH
    end

    subgraph EVICTION["Eviction Policies"]
        E1["allkeys-lru\n(default policy)\nEvict least recently used\nwhen memory full"]
        E2["Cache invalidation:\n- On data update event\n- On TTL expiry\n- On explicit DELETE"]
    end
```

---

## 8.3 Neo4j Knowledge Graph Schema

```mermaid
flowchart LR
    subgraph NODES["Node Types"]
        NOTE["(:KnowledgeNote)\n- note_id\n- title\n- content\n- tags[]\n- created_at\n- source"]
        TOPIC["(:Topic)\n- name\n- category"]
        STOCK_NODE["(:Stock)\n- symbol\n- name\n- exchange"]
        CONCEPT["(:Concept)\n- name\n- definition\n- domain"]
    end

    subgraph RELATIONSHIPS["Relationships"]
        REL1["NOTE -[:RELATED_TO]-> NOTE\nSemantic similarity"]
        REL2["NOTE -[:ABOUT]-> TOPIC\nNote topic classification"]
        REL3["NOTE -[:MENTIONS]-> STOCK_NODE\nStock mentions in notes"]
        REL4["NOTE -[:EXPLAINS]-> CONCEPT\nConcept definitions"]
        REL5["TOPIC -[:CHILD_OF]-> TOPIC\nHierarchy"]
        REL6["CONCEPT -[:APPLIES_TO]-> STOCK_NODE\nConcept applications"]
    end

    subgraph QUERIES["Cypher Query Patterns"]
        Q1["// Find related notes\nMATCH (n:KnowledgeNote)-[:RELATED_TO*1..2]-(related)\nWHERE n.note_id = $id\nRETURN related\nORDER BY related.relevance_score DESC\nLIMIT 10"]
        Q2["// Semantic search\nMATCH (n:KnowledgeNote)\nWHERE n.content CONTAINS $query\n   OR ANY(tag IN n.tags WHERE tag CONTAINS $query)\nRETURN n, score(n) as relevance\nORDER BY relevance DESC"]
        Q3["// Graph stats\nMATCH (n:KnowledgeNote)\nRETURN count(n) as total_notes,\n  count(DISTINCT labels(n)) as node_types"]
    end
```

---

## 8.4 Data Flow — Market Data Pipeline

```mermaid
flowchart TD
    subgraph SOURCE["External Data Sources"]
        VCI["VNStock VCI\nReal-time prices\nCompany data\nFinancial reports"]
        SSI["SSI Data\n(fallback source)"]
        NEWS["News APIs\n(for AI sentiment)"]
    end

    subgraph INGESTION["Data Ingestion Layer (stock-data-service)"]
        SYNC_JOB["Background Sync Job\nAPScheduler\n01:00 AM daily\n+ manual trigger"]
        VNSTOCK_SDK["VNStock Python SDK\nvnstock.Quote(symbol)\nvnstock.Company(symbol)"]
        PARSER["Data Parser\nCSV / JSON → ORM models\ndate normalization\nprice validation"]
    end

    subgraph STORAGE["Storage Layer"]
        MYSQL_STOCK["MySQL\nstocks table\ncompanies table\nindustries table"]
        REDIS_CACHE["Redis\nstock:{symbol} TTL=5min\npriceboard:vn30 TTL=5s"]
        MQ_EVENT["RabbitMQ\nstock.price.updated\nstock.company.synced"]
    end

    subgraph CONSUMERS["Data Consumers"]
        PORT_SVC_C["portfolio-service\nrecalculates holdings value"]
        PRED_SVC_C["prediction-service\nqueues re-prediction jobs"]
        ANAL_SVC_C["analysis-service\nrecomputes technical indicators"]
        AI_SVC_C["ai-insights-service\nrefreshes cached insights"]
    end

    VCI --> VNSTOCK_SDK
    SSI -.->|"fallback"| VNSTOCK_SDK
    VNSTOCK_SDK --> PARSER
    PARSER --> MYSQL_STOCK
    PARSER --> REDIS_CACHE
    PARSER --> MQ_EVENT

    MQ_EVENT --> PORT_SVC_C
    MQ_EVENT --> PRED_SVC_C
    MQ_EVENT --> ANAL_SVC_C
    MQ_EVENT --> AI_SVC_C

    NEWS --> AI_SVC_C

    style SOURCE fill:#e0f2fe,stroke:#0284c7
    style INGESTION fill:#fef9c3,stroke:#ca8a04
    style STORAGE fill:#fee2e2,stroke:#ef4444
    style CONSUMERS fill:#dcfce7,stroke:#22c55e
```

---

## 8.5 Database Connection Architecture

```mermaid
flowchart TD
    subgraph SERVICES["Microservices"]
        S1["auth-service"]
        S2["stock-data-service"]
        S3["portfolio-service"]
        S4["prediction-service"]
        S5["journal-service"]
    end

    subgraph CONN_POOL["SQLAlchemy Async Engine (stock-common)"]
        ENGINE["create_async_engine(\n  url=DATABASE_URL,\n  pool_size=5,\n  max_overflow=10,\n  pool_pre_ping=True,\n  pool_recycle=3600\n)"]
        SESSION_FACTORY["async_sessionmaker(\n  bind=engine,\n  expire_on_commit=False\n)"]
        SCOPE["Scoped Session\nper HTTP request\n(FastAPI dependency)"]
    end

    subgraph DB_TIER["Database Tier"]
        subgraph LOCAL["Dev: Local MySQL\nprofile: local-db\nlocalhost:3309"]
            MYSQL_LOCAL["MySQL 8\n(docker container)"]
        end
        subgraph REMOTE["Prod: Remote MySQL\n(via SSH tunnel)"]
            SSH_TUNNEL["SSH Tunnel Container\nhost.docker.internal:3306\n→ remote MySQL"]
            MYSQL_REMOTE["Remote MySQL\n(production DB)"]
        end
    end

    S1 & S2 & S3 & S4 & S5 --> ENGINE
    ENGINE --> SESSION_FACTORY
    SESSION_FACTORY --> SCOPE
    SCOPE --> LOCAL
    SCOPE -.->|"profile: remote-db"| REMOTE
    SSH_TUNNEL --> MYSQL_REMOTE

    style CONN_POOL fill:#f3e8ff,stroke:#9333ea
    style LOCAL fill:#dcfce7,stroke:#22c55e
    style REMOTE fill:#dbeafe,stroke:#3b82f6
```
