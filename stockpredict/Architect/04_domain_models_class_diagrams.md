# 04 — Domain Models & Class Diagrams

## 4.1 Auth Service — Domain Model

```mermaid
classDiagram
    class User {
        +int id
        +String username
        +String email
        +String hashed_password
        +String role  // user | admin | premium
        +bool is_active
        +bool is_verified
        +DateTime created_at
        +DateTime updated_at
        +login(password) JWT
        +changePassword(old, new) void
        +generateRefreshToken() RefreshToken
    }

    class RefreshToken {
        +int id
        +int user_id
        +String token
        +DateTime expires_at
        +bool is_revoked
        +DateTime created_at
        +revoke() void
        +isValid() bool
    }

    class JWTPayload {
        +int sub  // user_id
        +String role
        +DateTime exp
        +DateTime iat
        +String jti
    }

    User "1" --> "0..*" RefreshToken : has
    User ..> JWTPayload : generates
```

---

## 4.2 Stock Data Service — Domain Model

```mermaid
classDiagram
    class Company {
        +String symbol PK
        +String name
        +String name_en
        +String exchange  // HOSE | HNX | UPCOM
        +int industry_id FK
        +String description
        +int founded_year
        +String website
        +String address
        +float market_cap
        +DateTime listed_date
        +DateTime updated_at
    }

    class Stock {
        +int id PK
        +String symbol FK
        +float open_price
        +float high_price
        +float low_price
        +float close_price
        +float volume
        +Date trade_date
        +String source  // VCI | SSI | etc
    }

    class Industry {
        +int id PK
        +String name
        +String name_en
        +String sector
        +String icb_code
    }

    class PriceBoard {
        +String symbol
        +float price
        +float change
        +float change_percent
        +float volume
        +float value
        +float buy1 buy2 buy3
        +float sell1 sell2 sell3
        +String status
        +DateTime updated_at
    }

    class MarketIndex {
        +String code  // VNINDEX | VN30 | HNX
        +float value
        +float change
        +float change_percent
        +float volume
        +DateTime timestamp
    }

    Industry "1" --> "0..*" Company : classifies
    Company "1" --> "0..*" Stock : has history
    Company "1" --> "1" PriceBoard : has live price
```

---

## 4.3 Portfolio Service — Domain Model

```mermaid
classDiagram
    class Portfolio {
        +int id PK
        +int user_id FK
        +String name
        +String description
        +float initial_capital
        +float cash_balance
        +DateTime created_at
        +DateTime updated_at
        +getTotalValue() float
        +getPnL() float
        +getReturnPct() float
    }

    class Holding {
        +int id PK
        +int portfolio_id FK
        +String symbol
        +float quantity
        +float avg_cost
        +float current_price
        +DateTime last_updated
        +getMarketValue() float
        +getUnrealizedPnL() float
    }

    class Transaction {
        +int id PK
        +int portfolio_id FK
        +String symbol
        +String type  // BUY | SELL
        +float quantity
        +float price
        +float fee
        +float total_amount
        +DateTime trade_date
        +String notes
    }

    class Alert {
        +int id PK
        +int user_id FK
        +String symbol
        +String alert_type  // PRICE_ABOVE | PRICE_BELOW | PCT_CHANGE
        +float target_value
        +bool is_active
        +bool is_triggered
        +DateTime triggered_at
        +DateTime created_at
        +check(currentPrice) bool
    }

    class Watchlist {
        +int id PK
        +int user_id FK
        +String name
        +List~String~ symbols
        +DateTime created_at
    }

    Portfolio "1" --> "0..*" Holding : contains
    Portfolio "1" --> "0..*" Transaction : records
    Portfolio ..> Alert : triggers
    Portfolio ..> Watchlist : manages
```

---

## 4.4 Prediction Service — Domain Model

```mermaid
classDiagram
    class MLModel {
        +int id PK
        +String name
        +String model_type  // LSTM | GRF | LINEAR | XGB
        +String symbol
        +String status  // PENDING | TRAINING | READY | FAILED
        +String version
        +float accuracy
        +float mse
        +JSON hyperparameters
        +String file_path
        +DateTime trained_at
        +DateTime created_at
        +train(data) void
        +predict(input) PredictionResult
    }

    class Solution {
        +int id PK
        +String name
        +String description
        +List~MLModel~ models
        +String ensemble_method
        +DateTime created_at
        +predict(symbol, horizon) PredictionResult
    }

    class PredictionResult {
        +int id PK
        +int model_id FK
        +String symbol
        +int horizon_days
        +float predicted_price
        +float confidence
        +JSON prediction_series
        +DateTime predicted_at
        +DateTime target_date
    }

    class TechnicalIndicator {
        +int id PK
        +String name  // RSI | MACD | BB | SMA | EMA
        +String formula
        +JSON parameters
        +String category
    }

    class TimeSeries {
        +int id PK
        +String symbol
        +String series_type  // PRICE | VOLUME | INDICATOR
        +JSON data_points
        +Date start_date
        +Date end_date
        +String frequency  // D | W | M
    }

    class BacktestResult {
        +int id PK
        +int model_id FK
        +String symbol
        +Date start_date
        +Date end_date
        +float total_return
        +float sharpe_ratio
        +float max_drawdown
        +float win_rate
        +JSON trades
    }

    MLModel "1" --> "0..*" PredictionResult : produces
    Solution "1" --> "1..*" MLModel : uses
    MLModel "1" --> "0..*" BacktestResult : has
    MLModel ..> TechnicalIndicator : uses features
    TimeSeries ..> MLModel : trains
```

---

## 4.5 Analysis Service — Domain Model

```mermaid
classDiagram
    class TechnicalAnalysis {
        +String symbol
        +Date analysis_date
        +float rsi_14
        +float macd
        +float macd_signal
        +float macd_hist
        +float bb_upper
        +float bb_middle
        +float bb_lower
        +float sma_20
        +float sma_50
        +float sma_200
        +float ema_12
        +float ema_26
        +float volume_sma
        +String trend  // BULLISH | BEARISH | SIDEWAYS
        +float support_level
        +float resistance_level
    }

    class FundamentalAnalysis {
        +String symbol
        +int year
        +int quarter
        +float revenue
        +float gross_profit
        +float net_income
        +float eps
        +float pe_ratio
        +float pb_ratio
        +float roe
        +float roa
        +float debt_to_equity
        +float current_ratio
        +float dividend_yield
    }

    class ScreenerFilter {
        +String filter_type
        +String field
        +String operator  // GT | LT | EQ | BETWEEN
        +float value
        +float value2
        +apply(stocks) List~Stock~
    }

    class AnalysisPattern {
        +String symbol
        +String pattern_name  // HEAD_SHOULDERS | DOUBLE_TOP | etc
        +float confidence
        +String signal  // BUY | SELL | NEUTRAL
        +Date detected_date
        +JSON pattern_data
    }

    TechnicalAnalysis --> AnalysisPattern : detects
    ScreenerFilter ..> TechnicalAnalysis : filters
    ScreenerFilter ..> FundamentalAnalysis : filters
```

---

## 4.6 Journal Service — Domain Model

```mermaid
classDiagram
    class TradingAccount {
        +int id PK
        +int user_id FK
        +String name
        +String broker
        +float initial_capital
        +float current_balance
        +String currency
        +DateTime created_at
        +getEquity() float
        +getRiskCapital() float
    }

    class TradingRule {
        +int id PK
        +int account_id FK
        +String name
        +String description
        +String rule_type  // ENTRY | EXIT | RISK | POSITION
        +bool is_active
        +checkCompliance(trade) bool
    }

    class Trade {
        +int id PK
        +int account_id FK
        +String symbol
        +String direction  // LONG | SHORT
        +String status  // PLANNED | OPEN | CLOSED
        +float entry_price
        +float exit_price
        +float stop_loss
        +float take_profit
        +float quantity
        +float pnl
        +float risk_amount
        +float reward_amount
        +float rr_ratio
        +DateTime entry_date
        +DateTime exit_date
        +String setup_type
        +String notes
        +calculateRR() float
        +calculatePnL() float
    }

    class TradeDiary {
        +int id PK
        +int trade_id FK
        +String content
        +String emotion  // CONFIDENT | FEARFUL | NEUTRAL
        +String chart_url
        +DateTime created_at
    }

    class DailyPlan {
        +int id PK
        +int account_id FK
        +Date plan_date
        +String market_context
        +String planned_trades
        +float max_risk_today
        +String goals
        +String review
        +bool completed
    }

    class WeeklyReview {
        +int id PK
        +int account_id FK
        +Date week_start
        +Date week_end
        +float total_pnl
        +int total_trades
        +int winning_trades
        +float win_rate
        +float profit_factor
        +String lessons_learned
        +String next_week_focus
    }

    class EquitySnapshot {
        +int id PK
        +int account_id FK
        +Date snapshot_date
        +float equity
        +float drawdown
        +float drawdown_pct
    }

    TradingAccount "1" --> "0..*" TradingRule : enforces
    TradingAccount "1" --> "0..*" Trade : records
    TradingAccount "1" --> "0..*" DailyPlan : has
    TradingAccount "1" --> "0..*" WeeklyReview : has
    TradingAccount "1" --> "0..*" EquitySnapshot : tracks
    Trade "1" --> "0..*" TradeDiary : documented by
```

---

## 4.7 Knowledge QA Service — Domain Entities

```mermaid
classDiagram
    class ChatSession {
        +String session_id
        +String user_id
        +List~ChatMessage~ messages
        +DateTime created_at
        +DateTime last_active
        +addMessage(msg) void
        +getHistory() List~ChatMessage~
        +clear() void
    }

    class ChatMessage {
        +String message_id
        +String session_id
        +String role  // user | assistant
        +String content
        +List~NoteReference~ references
        +DateTime timestamp
    }

    class KnowledgeNote {
        +String note_id
        +String title
        +String content
        +List~String~ tags
        +String source
        +DateTime created_at
        +toEmbedding() Vector
    }

    class SearchQuery {
        <<value object>>
        +String query_text
        +int max_results
        +List~String~ filters
        +normalize() SearchQuery
    }

    class GraphContext {
        <<value object>>
        +List~KnowledgeNote~ relevant_notes
        +List~String~ relationships
        +float relevance_score
        +format() String
    }

    class LLMResponse {
        <<value object>>
        +String answer
        +List~NoteReference~ citations
        +float confidence
        +String model_used
    }

    class NoteReference {
        <<value object>>
        +String note_id
        +String title
        +float relevance_score
        +String excerpt
    }

    ChatSession "1" --> "0..*" ChatMessage : contains
    ChatMessage --> "0..*" NoteReference : cites
    SearchQuery ..> GraphContext : produces
    GraphContext ..> LLMResponse : generates
    GraphContext ..> KnowledgeNote : wraps
```

---

## 4.8 Shared Stock-Common — Core Classes

```mermaid
classDiagram
    class BaseRepository~T~ {
        <<abstract>>
        #AsyncSession session
        +get(id) T
        +get_all(skip, limit) List~T~
        +create(obj) T
        +update(id, data) T
        +delete(id) bool
        +exists(id) bool
        #_build_query(filters) Query
    }

    class EventBus {
        -RobustConnection connection
        -Dict~str, Channel~ channels
        +connect() void
        +disconnect() void
        +publish(event, routing_key) void
        +subscribe(pattern, handler) void
        +declare_exchange(name, type) void
        -_handle_reconnect() void
        -_dead_letter_queue(msg) void
    }

    class Event {
        +String event_id
        +String event_type
        +EventMetadata metadata
        +Dict payload
        +DateTime occurred_at
        +String version
    }

    class EventMetadata {
        +String correlation_id
        +String causation_id
        +String user_id
        +String source_service
        +int retry_count
    }

    class CircuitBreaker {
        -String state  // CLOSED | OPEN | HALF_OPEN
        -int failure_count
        -int failure_threshold
        -DateTime next_attempt
        +call(func) Any
        +_on_success() void
        +_on_failure() void
        +_can_attempt() bool
    }

    class ResilientClient {
        +CircuitBreaker breaker
        +RetryPolicy retry
        +Timeout timeout
        +get(url, **kwargs) Response
        +post(url, data, **kwargs) Response
        -_execute_with_resilience(func) Any
    }

    class JWTManager {
        -String secret_key
        -String algorithm  // HS256
        -int expire_minutes
        +create_access_token(data) str
        +create_refresh_token(user_id) str
        +verify_token(token) JWTPayload
        +decode_token(token) Dict
    }

    BaseRepository ..> Event : uses
    EventBus ..> Event : routes
    Event ..> EventMetadata : carries
    ResilientClient ..> CircuitBreaker : uses
    JWTManager ..> JWTPayload : creates
```
