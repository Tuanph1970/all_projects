# 05 — Event-Driven Architecture

## 5.1 RabbitMQ Topology Overview

```mermaid
flowchart TD
    subgraph PRODUCERS["Event Producers"]
        STOCK_P["stock-data-service\n(Publisher)"]
        PRED_P["prediction-service\n(Publisher)"]
        PORT_P["portfolio-service\n(Publisher)"]
        ANAL_P["analysis-service\n(Publisher)"]
        AUTH_P["auth-service\n(Publisher)"]
        CHAT_P["chatbot-service\n(Publisher)"]
    end

    subgraph RABBITMQ["RabbitMQ Broker\nvhost: /stock"]
        subgraph EXCHANGE["Topic Exchange: stock.events"]
            EX["stock.events\n(topic type\ndurable=true)"]
        end

        subgraph DLX["Dead Letter Exchange"]
            DLQ["stock.events.dlq\n(failed messages\nmax-retries=3)"]
        end

        subgraph QUEUES["Queues (durable, persistent)"]
            Q1["stock.data.queue\nrouting: stock.#"]
            Q2["prediction.queue\nrouting: prediction.#"]
            Q3["portfolio.queue\nrouting: portfolio.#"]
            Q4["analysis.queue\nrouting: analysis.#"]
            Q5["auth.queue\nrouting: auth.#"]
            Q6["chatbot.queue\nrouting: chatbot.#"]
            Q7["dlq.queue\nfailed messages"]
        end
    end

    subgraph CONSUMERS["Event Consumers"]
        PORT_C["portfolio-service\n(Consumer)"]
        PRED_C["prediction-service\n(Consumer)"]
        ANAL_C["analysis-service\n(Consumer)"]
        NOTIF_C["notification\n(future Consumer)"]
    end

    STOCK_P -->|"publish"| EX
    PRED_P -->|"publish"| EX
    PORT_P -->|"publish"| EX
    ANAL_P -->|"publish"| EX
    AUTH_P -->|"publish"| EX
    CHAT_P -->|"publish"| EX

    EX -->|"stock.#"| Q1
    EX -->|"prediction.#"| Q2
    EX -->|"portfolio.#"| Q3
    EX -->|"analysis.#"| Q4
    EX -->|"auth.#"| Q5
    EX -->|"chatbot.#"| Q6
    EX -->|"x-dead-letter"| DLQ
    DLQ --> Q7

    Q1 --> PORT_C
    Q1 --> PRED_C
    Q2 --> ANAL_C
    Q3 --> NOTIF_C

    style RABBITMQ fill:#fef9c3,stroke:#ca8a04
    style PRODUCERS fill:#dbeafe,stroke:#3b82f6
    style CONSUMERS fill:#dcfce7,stroke:#22c55e
    style DLX fill:#fee2e2,stroke:#ef4444
```

---

## 5.2 Complete Event Catalog

```mermaid
mindmap
  root((Domain Events))
    Stock Domain
      stock.price.updated
        payload: symbol, price, change, timestamp
        producer: stock-data-service
        consumers: portfolio-service
      stock.company.synced
        payload: symbol, company_data
        producer: stock-data-service
        consumers: analysis-service
      stock.data.available
        payload: symbol, date_range
        producer: stock-data-service
        consumers: prediction-service
      stock.sync.requested
        payload: symbols, source
        producer: scheduler
      stock.sync.completed
        payload: symbols_updated, duration
        producer: stock-data-service
    Prediction Domain
      prediction.training.started
        payload: model_id, symbol, config
        producer: prediction-service
      prediction.training.progress
        payload: model_id, epoch, loss, accuracy
        producer: prediction-service
      prediction.training.completed
        payload: model_id, metrics
        producer: prediction-service
      prediction.training.failed
        payload: model_id, error
        producer: prediction-service
      prediction.generated
        payload: symbol, horizon, predicted_price
        producer: prediction-service
      prediction.model.created
        payload: model_id, name, type
        producer: prediction-service
    Portfolio Domain
      portfolio.updated
        payload: portfolio_id, change_type
        producer: portfolio-service
      portfolio.stock.added
        payload: portfolio_id, symbol, quantity
        producer: portfolio-service
      portfolio.transaction.completed
        payload: transaction_id, type, symbol
        producer: portfolio-service
      portfolio.alert.triggered
        payload: alert_id, symbol, price
        producer: portfolio-service
    Analysis Domain
      analysis.completed
        payload: symbol, analysis_type, date
        producer: analysis-service
      analysis.pattern.detected
        payload: symbol, pattern, confidence
        producer: analysis-service
      analysis.requested
        payload: symbol, types
        producer: api requests
    Auth Domain
      auth.user.registered
        payload: user_id, email
        producer: auth-service
      auth.user.logged_in
        payload: user_id, timestamp, ip
        producer: auth-service
      auth.password.changed
        payload: user_id
        producer: auth-service
    AI Domain
      ai.insight.generated
        payload: symbol, insight_type, summary
        producer: ai-insights-service
      ai.sentiment.analyzed
        payload: symbol, sentiment, score
        producer: ai-insights-service
```

---

## 5.3 Event Structure & Envelope

```mermaid
classDiagram
    class Event {
        +String event_id       // UUID v4
        +String event_type     // stock.price.updated
        +String version        // "1.0"
        +DateTime occurred_at
        +EventMetadata metadata
        +Dict payload          // domain-specific data
    }

    class EventMetadata {
        +String correlation_id  // trace across services
        +String causation_id    // parent event that caused this
        +String user_id         // originating user (if applicable)
        +String source_service  // stock-data-service
        +int retry_count        // DLQ retry counter
        +String tenant_id       // future multi-tenancy
    }

    class PublishedMessage {
        +String routing_key     // stock.price.updated
        +int delivery_mode      // 2 = persistent
        +String content_type    // application/json
        +String message_id      // event_id
        +String correlation_id  // from metadata
        +bytes body             // JSON-encoded Event
    }

    class ConsumedMessage {
        +PublishedMessage message
        +ack() void
        +nack(requeue) void
        +reject() void
    }

    Event ..> EventMetadata : carries
    Event ..> PublishedMessage : serialized as
    PublishedMessage ..> ConsumedMessage : received as
```

---

## 5.4 Event Flow — Stock Price Update Cascade

```mermaid
sequenceDiagram
    autonumber
    participant SCHED as Scheduler (APScheduler)
    participant STOCK as stock-data-service
    participant MQ as RabbitMQ
    participant PORT as portfolio-service
    participant PRED as prediction-service
    participant NOTIF as Notification (future)

    SCHED->>STOCK: trigger daily sync (01:00 AM)
    STOCK->>STOCK: Pull data from VNStock/VCI
    STOCK->>STOCK: UPDATE stocks table
    STOCK->>MQ: PUBLISH stock.price.updated\n{symbol: "VNM", price: 85500, change: +0.5%}
    STOCK->>MQ: PUBLISH stock.company.synced\n{symbol: "VNM", company_data: {...}}
    STOCK->>MQ: PUBLISH stock.sync.completed\n{updated_count: 450}

    MQ-->>PORT: DELIVER stock.price.updated
    PORT->>PORT: Query holdings with VNM
    PORT->>PORT: Recalculate portfolio values
    PORT->>PORT: Check price alerts (85500 > alert.target?)
    alt Alert triggered
        PORT->>MQ: PUBLISH portfolio.alert.triggered\n{alert_id, symbol, price}
        MQ-->>NOTIF: DELIVER alert.triggered
        NOTIF->>NOTIF: Send push notification (future)
    end
    PORT->>MQ: ACK message

    MQ-->>PRED: DELIVER stock.data.available
    PRED->>PRED: Identify models scheduled for VNM
    PRED->>PRED: Queue re-prediction job
    PRED->>MQ: PUBLISH prediction.generated\n{symbol: "VNM", predicted_price: 86200}
    PRED->>MQ: ACK message
```

---

## 5.5 Dead Letter Queue Flow

```mermaid
flowchart TD
    MSG["Incoming Message\nfrom exchange"] --> CONSUMER

    CONSUMER["Consumer\n(any service)"]
    CONSUMER -->|"Processing error\nor timeout"| NACK["nack(requeue=False)"]
    NACK --> DLX["Dead Letter Exchange\nstock.events.dlq"]
    DLX --> DLQ["Dead Letter Queue\nstock.dlq.queue"]

    DLQ --> RETRY_CHECK{"retry_count\n< max_retries?"}
    RETRY_CHECK -->|"Yes (retry_count++)"| DELAY["Delay Exchange\n(exponential backoff)\n1s → 5s → 30s"]
    DELAY --> EXCHANGE["Original Exchange\nstock.events"]
    EXCHANGE --> CONSUMER

    RETRY_CHECK -->|"No (exhausted)"| DEAD_STORE["Dead Message Store\n(DB or S3 for audit)"]
    DEAD_STORE --> ALERT["Alert Operations\n(Grafana alarm)"]

    style DLQ fill:#fee2e2,stroke:#ef4444
    style DEAD_STORE fill:#fef9c3,stroke:#ca8a04
```

---

## 5.6 EventBus Implementation Pattern

```mermaid
flowchart LR
    subgraph PUBLISHER["Publisher Side"]
        SVC_CODE["Service Code\nbusiness logic"]
        EB_PUB["EventBus.publish(\n  event,\n  routing_key\n)"]
        SERIALIZER["JSON Serializer\n+ envelope"]
        CHANNEL["aio_pika Channel\nexchange.publish()"]
    end

    subgraph SUBSCRIBER["Subscriber Side"]
        DECORATOR["@event_handler(\n  'stock.price.*'\n)"]
        REGISTRY["EventHandlerRegistry\npattern matching"]
        HANDLER["async handler_fn(\n  event: Event\n) -> None"]
        ACK_LOGIC["ack() / nack()\nbased on result"]
    end

    SVC_CODE --> EB_PUB
    EB_PUB --> SERIALIZER
    SERIALIZER --> CHANNEL

    CHANNEL --> REGISTRY
    REGISTRY -->|"pattern match"| DECORATOR
    DECORATOR --> HANDLER
    HANDLER --> ACK_LOGIC
```
