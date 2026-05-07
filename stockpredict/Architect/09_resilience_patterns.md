# 09 — Resilience Patterns

## 9.1 Resilience Stack (stock-common)

```mermaid
flowchart TD
    subgraph RESILIENT_CLIENT["ResilientClient (stock-common/resilience/)"]
        REQUEST["Incoming\nHTTP Request"]
        
        subgraph LAYERS["Defence Layers (applied in order)"]
            TIMEOUT["1. Timeout\ndefault: 30s\ntimeout.py\n→ asyncio.wait_for()"]
            BULKHEAD["2. Bulkhead\nbulkhead.py\nmax_concurrent=10\nsemaphore-based\nisolate failures"]
            CIRCUIT["3. Circuit Breaker\ncircuit_breaker.py\nfailure_threshold=5\nrecovery_timeout=60s"]
            RETRY["4. Retry\nretry.py (tenacity)\nmax_attempts=3\nexponential backoff\n1s → 2s → 4s"]
        end

        CALL["Execute actual\nHTTP call\n(httpx async)"]
        SUCCESS["Return response"]
        FAIL["Raise exception\n(after all retries)"]
    end

    REQUEST --> TIMEOUT
    TIMEOUT --> BULKHEAD
    BULKHEAD --> CIRCUIT
    CIRCUIT --> RETRY
    RETRY --> CALL
    CALL -->|"success"| SUCCESS
    CALL -->|"failure"| RETRY
    RETRY -->|"exhausted"| FAIL
    CIRCUIT -->|"OPEN state"| FAIL
    TIMEOUT -->|"TimeoutError"| FAIL
    BULKHEAD -->|"capacity exceeded"| FAIL
```

---

## 9.2 Circuit Breaker — State Machine Detail

```mermaid
stateDiagram-v2
    [*] --> CLOSED

    state CLOSED {
        [*] --> monitoring
        monitoring --> monitoring : success\n(failure_count stays 0)
        monitoring --> counting : failure_count++
        counting --> monitoring : success\n(reset failure_count=0)
        counting --> threshold_reached : failure_count >= 5
    }

    CLOSED --> OPEN : threshold_reached

    state OPEN {
        [*] --> blocking
        blocking : All requests\nimmediately rejected\nCircuitBreakerOpenError
        blocking --> timer_running : waiting 60s
    }

    OPEN --> HALF_OPEN : 60s elapsed

    state HALF_OPEN {
        [*] --> probe
        probe : One test request\nallowed through
    }

    HALF_OPEN --> CLOSED : probe succeeds\n(reset failure_count=0)
    HALF_OPEN --> OPEN : probe fails\n(reset 60s timer)

    note right of CLOSED
        Normal operation
        Track consecutive failures
    end note

    note right of OPEN
        Fast-fail for 60s
        Protects overloaded service
        Saves resources
    end note

    note right of HALF_OPEN
        Recovery testing
        One probe at a time
    end note
```

---

## 9.3 Retry Policy with Exponential Backoff

```mermaid
sequenceDiagram
    autonumber
    participant CLIENT as Service Client
    participant RETRY as Retry Wrapper\n(tenacity)
    participant TARGET as Target Service\n(external/internal)

    CLIENT->>RETRY: call(url, data)
    
    RETRY->>TARGET: Attempt 1
    TARGET-->>RETRY: 503 Service Unavailable
    Note over RETRY: Wait 1s (jitter ±0.3s)

    RETRY->>TARGET: Attempt 2
    TARGET-->>RETRY: 503 Service Unavailable
    Note over RETRY: Wait 2s (jitter ±0.6s)

    RETRY->>TARGET: Attempt 3
    TARGET-->>RETRY: 200 OK
    RETRY-->>CLIENT: Success response

    Note over RETRY,TARGET: If all 3 attempts fail:
    RETRY->>TARGET: Attempt 1
    TARGET-->>RETRY: 500 Error
    Note over RETRY: Wait 1s
    RETRY->>TARGET: Attempt 2
    TARGET-->>RETRY: 500 Error
    Note over RETRY: Wait 2s
    RETRY->>TARGET: Attempt 3
    TARGET-->>RETRY: 500 Error
    RETRY-->>CLIENT: MaxRetryError raised
```

---

## 9.4 Bulkhead Pattern — Resource Isolation

```mermaid
flowchart TD
    subgraph SERVICES["Services with Bulkheads"]
        subgraph AI_BULKHEAD["ai-insights-service Bulkhead"]
            AI_SEM["Semaphore(10)\nmax 10 concurrent\nLLM calls"]
            AI_Q["Queue overflow:\nfail fast with\n503 Too Many Requests"]
        end

        subgraph STOCK_BULKHEAD["stock-data-service Bulkhead"]
            STOCK_SEM["Semaphore(20)\nmax 20 concurrent\nVNStock API calls"]
            STOCK_Q["Queue: wait up to\n5s then fail"]
        end

        subgraph DB_BULKHEAD["Database Bulkhead\n(SQLAlchemy pool)"]
            DB_POOL["pool_size=5\nmax_overflow=10\nTotal: 15 max connections"]
            DB_WAIT["pool_timeout=30s\nthen QueuePool\noverflow error"]
        end
    end

    subgraph BENEFIT["Benefit: Failure Isolation"]
        B1["AI service overloaded\n→ only AI endpoints fail\n→ portfolio, market data\n   still serve normally"]
        B2["DB pool exhausted\n→ slow queries isolated\n→ cached reads\n   still work (Redis)"]
    end

    AI_SEM --> AI_Q
    STOCK_SEM --> STOCK_Q
    DB_POOL --> DB_WAIT
    AI_Q --> B1
    DB_WAIT --> B2

    style AI_BULKHEAD fill:#f3e8ff,stroke:#9333ea
    style STOCK_BULKHEAD fill:#dbeafe,stroke:#3b82f6
    style DB_BULKHEAD fill:#fef9c3,stroke:#ca8a04
```

---

## 9.5 Health Check Architecture

```mermaid
flowchart TD
    subgraph ENDPOINTS["Health Endpoints (every service)"]
        LIVE["/health/live\nLiveness probe\n→ 200 if process running\nno DB check\n(fast, always returns OK)"]
        READY["/health/ready\nReadiness probe\n→ 200 if DB + deps OK\n→ 503 if any dep down\n(controls traffic routing)"]
        HEALTH["/health\nDetailed status\n→ {status, db, redis,\n  rabbitmq, version}"]
        METRICS["/metrics\nPrometheus text format\n→ request counts\n→ latency histograms\n→ error rates"]
    end

    subgraph CONSUMERS["Health Check Consumers"]
        DOCKER_HC["Docker Compose\nhealthcheck:\n  test: curl /health/live\n  interval: 30s\n  timeout: 10s\n  retries: 3"]
        DEPLOY_SH["deploy.sh --health\nsweeps all service\nhealth endpoints"]
        TRAEFIK_HC["Traefik\nauto-removes unhealthy\ncontainers from rotation"]
        PROMETHEUS_H["Prometheus\nup{job='service'}\nmetric = 1 or 0"]
    end

    LIVE --> DOCKER_HC
    LIVE --> TRAEFIK_HC
    READY --> DEPLOY_SH
    METRICS --> PROMETHEUS_H
    HEALTH --> DEPLOY_SH

    style ENDPOINTS fill:#dcfce7,stroke:#22c55e
    style CONSUMERS fill:#dbeafe,stroke:#3b82f6
```

---

## 9.6 Timeout Hierarchy

```mermaid
flowchart LR
    subgraph TIMEOUTS["Timeout Layers (short to long)"]
        T1["Redis operation\n500ms\n(cache should be fast)"]
        T2["Internal service-to-service\n5s\n(same cluster)"]
        T3["VNStock data fetch\n10s\n(external API)"]
        T4["Database query\n15s\n(complex SQL)"]
        T5["OpenAI/Claude API\n60s\n(LLM generation)"]
        T6["ML model training\n3600s (1hr)\n(async job, not HTTP)"]
        T7["HTTP request total\n(ResilientClient)\n30s default"]
    end

    T1 --> T2 --> T3 --> T4 --> T5 --> T6
    T7 -.->|"wraps"| T2 & T3 & T4

    style T1 fill:#dcfce7
    style T5 fill:#fee2e2
    style T6 fill:#fef9c3
```
