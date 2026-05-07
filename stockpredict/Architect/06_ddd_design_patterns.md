# 06 — DDD & Design Patterns

## 6.1 Domain-Driven Design Layers Applied

```mermaid
flowchart TD
    subgraph PRESENTATION["Presentation Layer (API)"]
        ROUTES["FastAPI Routes\napi/routes.py\nHTTP verbs, path params\nPydantic request/response schemas"]
        HEALTH["Health Endpoints\n/health/live · /health/ready · /metrics"]
    end

    subgraph APPLICATION["Application Layer (Services)"]
        APP_SVC["Application Services\nservices/*.py\norchestrate domain objects\nno business rules here"]
        DTO["Pydantic Schemas\n(DTOs)\nRequest / Response models\nvalidation, serialization"]
        USECASE["Use Cases (knowledge-qa)\napplication/use_cases/*.py\nAskQuestion · SearchNotes\nGetChatHistory · GetStats"]
    end

    subgraph DOMAIN["Domain Layer (Core)"]
        ENTITIES["Domain Entities\nmodels/domain.py\nSQLAlchemy ORM\nbusiness invariants"]
        VALUE_OBJ["Value Objects (knowledge-qa)\nSearchQuery · GraphContext\nLLMResponse · NoteReference\nimmutable, no identity"]
        DOMAIN_SVC["Domain Services\nlogic spanning multiple entities\ne.g. PortfolioValuationService\nPredictionOrchestrator"]
        PORTS["Ports / Interfaces\n(knowledge-qa DDD)\nLLMPort · KnowledgeGraphRepo\nabstract, technology-neutral"]
        EVENTS["Domain Events\nEvent + EventMetadata\nstate changes as events"]
        AGGS["Aggregates\nPortfolio → Holdings\nTradingAccount → Trades\nChatSession → Messages"]
    end

    subgraph INFRASTRUCTURE["Infrastructure Layer"]
        REPOS["Repositories\nrepositories/*.py\nasync SQLAlchemy\nBaseRepository generic CRUD"]
        ADAPTERS["External Adapters\nOllamaAdapter\nOpenAIAdapter\nVNStockAdapter\nNeo4j repository"]
        EVENT_BUS["EventBus\nRabbitMQ aio-pika\npub/sub topology"]
        DB["Database\nMySQL / Redis / Neo4j"]
        CONFIG["Config\npydantic-settings\nenv vars injection"]
    end

    ROUTES --> APP_SVC
    ROUTES --> DTO
    APP_SVC --> DOMAIN_SVC
    APP_SVC --> ENTITIES
    APP_SVC --> USECASE
    DOMAIN_SVC --> ENTITIES
    DOMAIN_SVC --> PORTS
    ENTITIES --> AGGS
    PORTS -->|"impl"| REPOS
    PORTS -->|"impl"| ADAPTERS
    ADAPTERS --> DB
    REPOS --> DB
    APP_SVC --> EVENT_BUS
    EVENT_BUS --> EVENTS
    CONFIG --> INFRASTRUCTURE

    style PRESENTATION fill:#dbeafe,stroke:#3b82f6
    style APPLICATION fill:#dcfce7,stroke:#22c55e
    style DOMAIN fill:#f3e8ff,stroke:#9333ea
    style INFRASTRUCTURE fill:#fef9c3,stroke:#ca8a04
```

---

## 6.2 Repository Pattern

```mermaid
classDiagram
    class BaseRepository~T~ {
        <<abstract>>
        #AsyncSession session
        +get(id: int) T
        +get_all(skip: int, limit: int) List~T~
        +create(obj: T) T
        +update(id: int, data: dict) T
        +delete(id: int) bool
        +exists(id: int) bool
        #_build_query(filters: dict) Select
    }

    class UserRepository {
        +get_by_email(email) User
        +get_by_username(username) User
        +get_active_users() List~User~
        +search(query) List~User~
    }

    class StockRepository {
        +get_by_symbol(symbol) Stock
        +get_history(symbol, start, end) List~Stock~
        +get_latest(symbol) Stock
        +bulk_upsert(records) int
    }

    class PortfolioRepository {
        +get_by_user(user_id) List~Portfolio~
        +get_with_holdings(id) Portfolio
        +get_total_value(id) float
    }

    class HoldingRepository {
        +get_by_portfolio(portfolio_id) List~Holding~
        +upsert(portfolio_id, symbol, qty) Holding
        +get_by_symbol(symbol) List~Holding~
    }

    class ModelRepository {
        +get_ready_models(symbol) List~MLModel~
        +get_by_status(status) List~MLModel~
        +update_status(id, status, metrics) MLModel
    }

    class Neo4jKnowledgeGraphRepository {
        <<implements KnowledgeGraphPort>>
        -Neo4jDriver driver
        +search_notes(query: SearchQuery) List~KnowledgeNote~
        +get_related_notes(note_id) List~KnowledgeNote~
        +get_graph_stats() Dict
        +find_path(source_id, target_id) List~Node~
    }

    BaseRepository <|-- UserRepository
    BaseRepository <|-- StockRepository
    BaseRepository <|-- PortfolioRepository
    BaseRepository <|-- HoldingRepository
    BaseRepository <|-- ModelRepository
    Neo4jKnowledgeGraphRepository --|> KnowledgeGraphPort

    class KnowledgeGraphPort {
        <<interface>>
        +search_notes(query) List~KnowledgeNote~
        +get_graph_stats() Dict
    }
```

---

## 6.3 Factory Pattern (Prediction Service)

```mermaid
classDiagram
    class ModelFactory {
        <<abstract>>
        +create(config: ModelConfig) BaseMLModel
        +get_supported_types() List~str~
    }

    class LSTMModelFactory {
        +create(config) LSTMModel
    }

    class XGBoostModelFactory {
        +create(config) XGBoostModel
    }

    class LinearModelFactory {
        +create(config) LinearRegressionModel
    }

    class GRFModelFactory {
        +create(config) GradientRandomForestModel
    }

    class BaseMLModel {
        <<abstract>>
        +train(X, y) void
        +predict(X) PredictionResult
        +evaluate(X_test, y_test) Metrics
        +save(path) void
        +load(path) void
    }

    class LSTMModel {
        +train(X, y) void
        +predict(X) PredictionResult
        -_build_network() Sequential
        -_preprocess(data) ndarray
    }

    class XGBoostModel {
        +train(X, y) void
        +predict(X) PredictionResult
    }

    class ModelConfig {
        +String model_type
        +String symbol
        +int lookback_days
        +int horizon_days
        +Dict hyperparameters
        +List~String~ features
    }

    ModelFactory <|-- LSTMModelFactory
    ModelFactory <|-- XGBoostModelFactory
    ModelFactory <|-- LinearModelFactory
    ModelFactory <|-- GRFModelFactory
    ModelFactory ..> ModelConfig : uses
    LSTMModelFactory ..> LSTMModel : creates
    XGBoostModelFactory ..> XGBoostModel : creates
    BaseMLModel <|-- LSTMModel
    BaseMLModel <|-- XGBoostModel
```

---

## 6.4 Strategy Pattern (Analysis Service)

```mermaid
classDiagram
    class IndicatorStrategy {
        <<interface>>
        +calculate(prices: List~float~, **params) Dict
        +get_signal(values: Dict) str
        +get_name() str
    }

    class RSIStrategy {
        +calculate(prices, period=14) Dict
        +get_signal(values) str  // OVERSOLD|OVERBOUGHT|NEUTRAL
    }

    class MACDStrategy {
        +calculate(prices, fast=12, slow=26, signal=9) Dict
        +get_signal(values) str  // BULLISH_CROSS|BEARISH_CROSS|NEUTRAL
    }

    class BollingerBandStrategy {
        +calculate(prices, period=20, std_dev=2) Dict
        +get_signal(values) str  // UPPER_BREACH|LOWER_BREACH|NEUTRAL
    }

    class SMAStrategy {
        +calculate(prices, period=50) Dict
        +get_signal(values) str
    }

    class AnalysisContext {
        -IndicatorStrategy[] strategies
        +add_strategy(strategy) void
        +run_all(prices) List~IndicatorResult~
        +get_composite_signal() str
        +get_trend_strength() float
    }

    IndicatorStrategy <|.. RSIStrategy
    IndicatorStrategy <|.. MACDStrategy
    IndicatorStrategy <|.. BollingerBandStrategy
    IndicatorStrategy <|.. SMAStrategy
    AnalysisContext ..> IndicatorStrategy : uses
```

---

## 6.5 Observer Pattern (Alert System)

```mermaid
classDiagram
    class PriceObserver {
        <<interface>>
        +update(symbol: str, price: float) void
    }

    class AlertObserver {
        -AlertRepository repo
        +update(symbol, price) void
        -_check_alerts(symbol, price) List~Alert~
        -_trigger(alert, price) void
    }

    class PortfolioObserver {
        -PortfolioRepository repo
        +update(symbol, price) void
        -_recalculate_holdings(symbol, price) void
    }

    class PriceSubject {
        -List~PriceObserver~ observers
        -Dict~str,float~ prices
        +attach(observer) void
        +detach(observer) void
        +notify(symbol, price) void
        +set_price(symbol, price) void
    }

    class StockDataService {
        -PriceSubject subject
        +sync_prices() void
        +get_price(symbol) float
    }

    PriceObserver <|.. AlertObserver
    PriceObserver <|.. PortfolioObserver
    PriceSubject ..> PriceObserver : notifies
    StockDataService ..> PriceSubject : uses
```

---

## 6.6 Circuit Breaker Pattern

```mermaid
stateDiagram-v2
    [*] --> CLOSED : Initial State

    CLOSED --> CLOSED : Success\n(reset failure_count)
    CLOSED --> OPEN : failure_count >= threshold\n(default 5)

    OPEN --> OPEN : Request arrives\n(raise CircuitBreakerOpenError immediately)
    OPEN --> HALF_OPEN : Timeout elapsed\n(default 60s)

    HALF_OPEN --> CLOSED : Probe request succeeds\n(reset failure_count)
    HALF_OPEN --> OPEN : Probe request fails\n(reset timeout)

    note right of CLOSED
        Normal operation
        All requests pass through
        Tracks failures
    end note

    note right of OPEN
        Fast-fail mode
        Protects downstream service
        Saves resources
    end note

    note right of HALF_OPEN
        Testing mode
        One probe request allowed
        Decides recovery
    end note
```

---

## 6.7 CQRS Pattern (knowledge-qa-service)

```mermaid
flowchart LR
    subgraph API["API Layer"]
        POST_CHAT["POST /chat\n(command)"]
        GET_HIST["GET /history\n(query)"]
        GET_SRCH["GET /search\n(query)"]
        GET_STAT["GET /stats\n(query)"]
    end

    subgraph COMMANDS["Command Side (Write)"]
        CMD["AskQuestion\nCommand\n{session_id, question}"]
        UC_ASK["AskQuestion\nUseCase"]
        DOMAIN_SVC["QueryUnderstanding\nGraphRetrieval\nAnswerGeneration"]
        OLLAMA["Ollama LLM"]
        NEO4J_W["Neo4j Write\n(save session)"]
    end

    subgraph QUERIES["Query Side (Read)"]
        QRY_HIST["GetChatHistory\nQuery\n{session_id}"]
        QRY_SRCH["SearchNotes\nQuery\n{query_text}"]
        QRY_STAT["GetGraphStats\nQuery\n{}"]
        UC_HIST["GetChatHistory\nUseCase"]
        UC_SRCH["SearchNotes\nUseCase"]
        UC_STAT["GetGraphStats\nUseCase"]
        NEO4J_R["Neo4j Read\n(query graph)"]
        MEM_STORE["InMemory\nSession Store"]
    end

    POST_CHAT --> CMD
    GET_HIST --> QRY_HIST
    GET_SRCH --> QRY_SRCH
    GET_STAT --> QRY_STAT

    CMD --> UC_ASK
    UC_ASK --> DOMAIN_SVC
    DOMAIN_SVC --> OLLAMA
    DOMAIN_SVC --> NEO4J_W
    UC_ASK --> NEO4J_W

    QRY_HIST --> UC_HIST
    QRY_SRCH --> UC_SRCH
    QRY_STAT --> UC_STAT
    UC_HIST --> MEM_STORE
    UC_SRCH --> NEO4J_R
    UC_STAT --> NEO4J_R

    style COMMANDS fill:#dcfce7,stroke:#22c55e
    style QUERIES fill:#dbeafe,stroke:#3b82f6
```

---

## 6.8 Aggregate Pattern (Portfolio Service)

```mermaid
flowchart TD
    subgraph AGGREGATE["Portfolio Aggregate Root"]
        PORT["Portfolio\n(Aggregate Root)\nid, user_id, name\ncash_balance"]
        
        subgraph CHILDREN["Child Entities (same transaction boundary)"]
            HOLD["Holdings\n(Entity Collection)\nsymbol, quantity, avg_cost"]
            TXN["Transactions\n(Entity Collection)\ntype, qty, price, date"]
        end
        
        subgraph INVARIANTS["Business Invariants (enforced by Aggregate)"]
            INV1["cash_balance >= 0\n(cannot overdraw)"]
            INV2["BUY → reduce cash\nadd/update holding"]
            INV3["SELL → increase cash\nreduce/remove holding"]
            INV4["quantity >= 0\n(no negative positions)"]
        end
    end

    subgraph EXTERNAL["External References (by ID only)"]
        ALERT["Alert\n(different aggregate)\nuser_id, symbol, target"]
        WATCHLIST["Watchlist\n(different aggregate)\nuser_id, symbols[]"]
    end

    PORT --> HOLD
    PORT --> TXN
    PORT ..> INV1 & INV2 & INV3 & INV4
    PORT -.->|"user_id ref"| ALERT
    PORT -.->|"user_id ref"| WATCHLIST
```
