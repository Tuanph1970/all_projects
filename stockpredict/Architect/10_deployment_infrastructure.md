# 10 — Deployment & Infrastructure

## 10.1 Full-Stack Deployment Topology

```mermaid
flowchart TD
    subgraph HOST["Host Machine (Linux / Mac)"]
        BROWSER["Browser\nhttp://localhost:3004"]
        GW_PORT["Gateway Port\nhttp://localhost:8004"]

        subgraph COMPOSE_FULL["docker-compose.full-stack.yml"]
            
            subgraph FRONTEND_LAYER["Frontend Layer"]
                REACT_APP["stock-react-app\n:3004\nnginx serving CRA build\nProxy → gateway:8004"]
            end

            subgraph GATEWAY_LAYER["Gateway Layer"]
                TRAEFIK_FS["traefik\n:8004 (web)\n:8444 (tls)\n:8084 (dashboard)\nreads from microservices compose"]
            end

            subgraph MICROSERVICES_LAYER["Microservices (via import of stock_microservices/docker-compose.yml)"]
                AUTH_C["auth-service\n:8007"]
                STOCK_C["stock-data-service\n:8001"]
                PORT_C["portfolio-service\n:8003"]
                PRED_C["prediction-service\n:8002"]
                ANAL_C["analysis-service\n:8004i"]
                AI_C["ai-insights-service\n:8005"]
                CHAT_C["chatbot-service\n:8006"]
                JOUR_C["journal-service\n:8008"]
                QA_C["knowledge-qa-service\n:8009"]
            end

            subgraph DATA_LAYER["Data Layer"]
                MYSQL_C["mysql:8\n:3309 (external)\n:3306 (internal)\nprofile: local-db"]
                REDIS_C["redis:7-alpine\n:6382 (external)\n:6379 (internal)"]
                MQ_C["rabbitmq:3-management\n:5674 AMQP (external)\n:15674 UI (external)\nvhost: /stock"]
            end

            subgraph INFRA_LAYER["Infrastructure / AI"]
                SSH_C["ssh-tunnel\n:3306 (host.docker.internal)\nprofile: remote-db"]
                OLLAMA_GPU["ollama-gpu\n:11434\nNVIDIA GPU\nprofile: gpu"]
                OLLAMA_CPU["ollama-cpu\n:11434\nCPU fallback\nprofile: cpu"]
            end

            subgraph OBSERVABILITY_LAYER["Observability"]
                PROM_C["prometheus\n:9094 (external)\n:9090 (internal)\nscrapes all services"]
                GRAF_C["grafana\n:3100\ndashboards"]
                JAEGER_C["jaeger\n:16686 UI\n:4317 OTLP\ndistributed traces"]
            end
        end

        NEO4J_HOST["Neo4j (host process)\nbolt://host.docker.internal:7687\n(external to Docker)"]
        MYSQL_REMOTE["Remote MySQL\n(production)\nvia SSH tunnel"]
    end

    BROWSER --> REACT_APP
    REACT_APP --> TRAEFIK_FS
    GW_PORT --> TRAEFIK_FS
    TRAEFIK_FS --> AUTH_C & STOCK_C & PORT_C & PRED_C & ANAL_C & AI_C & CHAT_C & JOUR_C & QA_C

    AUTH_C & STOCK_C & PORT_C & PRED_C & JOUR_C --> MYSQL_C
    AI_C & CHAT_C & STOCK_C --> REDIS_C
    STOCK_C & PRED_C & PORT_C --> MQ_C
    QA_C --> NEO4J_HOST
    QA_C --> OLLAMA_GPU

    SSH_C -.-> MYSQL_REMOTE
    AUTH_C & STOCK_C -.->|"remote-db profile"| SSH_C

    AUTH_C & STOCK_C & PORT_C & PRED_C & ANAL_C --> PROM_C
    PROM_C --> GRAF_C
    AUTH_C & STOCK_C -.->|"OTLP"| JAEGER_C

    style HOST fill:#f8fafc
    style FRONTEND_LAYER fill:#dbeafe,stroke:#3b82f6
    style GATEWAY_LAYER fill:#fef9c3,stroke:#ca8a04
    style MICROSERVICES_LAYER fill:#dcfce7,stroke:#22c55e
    style DATA_LAYER fill:#fee2e2,stroke:#ef4444
    style OBSERVABILITY_LAYER fill:#f3e8ff,stroke:#9333ea
```

---

## 10.2 Port Allocation Map

```mermaid
block-beta
    columns 5
    block:H1["Service"]:1
    block:H2["Dev Port\n(microsvcs only)"]:1
    block:H3["Full-Stack Port\n(all-in-one)"]:1
    block:H4["Internal Port"]:1
    block:H5["Protocol"]:1

    A["Traefik (HTTP)"]:1 B["8004"]:1 C["8004"]:1 D["80"]:1 E["HTTP"]:1
    F["Traefik (HTTPS)"]:1 G["8444"]:1 H["8444"]:1 I["443"]:1 J["HTTPS"]:1
    K["Traefik Dashboard"]:1 L["8084"]:1 M["8084"]:1 N["8080"]:1 O["HTTP"]:1
    P["auth-service"]:1 Q["8007"]:1 R["8007"]:1 S["8007"]:1 T["HTTP"]:1
    U["stock-data-service"]:1 V["8001"]:1 W["8001"]:1 X["8001"]:1 Y["HTTP"]:1
    Z["portfolio-service"]:1 AA["8003"]:1 BB["8003"]:1 CC["8003"]:1 DD["HTTP"]:1
    EE["prediction-service"]:1 FF["8002"]:1 GG["8002"]:1 HH["8002"]:1 II["HTTP"]:1
    JJ["analysis-service"]:1 KK["8004i"]:1 LL["8004i"]:1 MM["8004i"]:1 NN["HTTP"]:1
    OO["ai-insights-service"]:1 PP["8005"]:1 QQ["8005"]:1 RR["8005"]:1 SS2["HTTP"]:1
    TT["chatbot-service"]:1 UU["8006"]:1 VV["8006"]:1 WW["8006"]:1 XX["HTTP"]:1
    YY["journal-service"]:1 ZZ["8008"]:1 AAA["8008"]:1 BBB["8008"]:1 CCC["HTTP"]:1
    DDD["knowledge-qa"]:1 EEE["8009"]:1 FFF["8009"]:1 GGG["8009"]:1 HHH["HTTP"]:1
    III["Frontend (React)"]:1 JJJ["3000 (dev)"]:1 KKK["3004"]:1 LLL["80"]:1 MMM["HTTP"]:1
    NNN["MySQL"]:1 OOO["-"]:1 PPP["3309"]:1 QQQ["3306"]:1 RRR["TCP"]:1
    SSS["Redis"]:1 TTT["-"]:1 UUU["6382"]:1 VVV["6379"]:1 WWW["TCP"]:1
    XXX["RabbitMQ AMQP"]:1 YYY["5672"]:1 ZZZ["5674"]:1 AAAA["5672"]:1 BBBB["AMQP"]:1
    CCCC["RabbitMQ UI"]:1 DDDD["15672"]:1 EEEE["15674"]:1 FFFF["15672"]:1 GGGG["HTTP"]:1
    HHHH["Prometheus"]:1 IIII["9090"]:1 JJJJ["9094"]:1 KKKK["9090"]:1 LLLL["HTTP"]:1
    MMMM["Grafana"]:1 NNNN["3100"]:1 OOOO["3100"]:1 PPPP["3000"]:1 QQQQ["HTTP"]:1
    RRRR["Jaeger UI"]:1 SSSS["16686"]:1 TTTT["16686"]:1 UUUU["16686"]:1 VVVV["HTTP"]:1
    WWWW["Ollama"]:1 XXXX["11434"]:1 YYYY["11434"]:1 ZZZZ["11434"]:1 AAAAA["HTTP"]:1
```

---

## 10.3 Docker Compose Networks

```mermaid
flowchart LR
    subgraph STOCK_NET["Docker Network: stock-network\n(bridge, internal)"]
        direction TB
        ALL_SVCS["All microservices\nauth, stock-data, portfolio,\nprediction, analysis,\nai-insights, chatbot,\njournal, knowledge-qa"]
        INFRA["Infrastructure\nMySQL, Redis,\nRabbitMQ, Traefik"]
        OBS["Observability\nPrometheus, Grafana, Jaeger"]
    end

    subgraph HOST_NET["Host Network Bridge\n(host.docker.internal)"]
        NEO4J_H["Neo4j\n:7687"]
        MYSQL_H["Remote MySQL\n(via SSH tunnel\n:3306)"]
        OLLAMA_H["Ollama\n:11434\n(if running on host)"]
    end

    FRONT_NET["Frontend\nstock-react-app\n(separate network\nor host port :3004)"]

    ALL_SVCS <--> INFRA
    INFRA <--> OBS
    ALL_SVCS -.->|"host.docker.internal"| HOST_NET
    FRONT_NET -->|":8004"| INFRA

    style STOCK_NET fill:#dbeafe,stroke:#3b82f6
    style HOST_NET fill:#dcfce7,stroke:#22c55e
```

---

## 10.4 CI/CD Pipeline

```mermaid
flowchart TD
    subgraph TRIGGER["Triggers"]
        PUSH_MAIN["Push to main"]
        PUSH_PR["Pull Request"]
        MANUAL["Manual dispatch"]
    end

    subgraph GHA[".github/workflows/ (GitHub Actions)"]
        subgraph LINT["Lint & Format"]
            PY_LINT["Python: flake8 + black\nstock_microservices/"]
            JS_LINT["JavaScript: ESLint\nstock_react_javascript/"]
        end

        subgraph TEST["Tests"]
            UNIT["Unit Tests\npytest services/*/tests\nnpm test (React)"]
            INT["Integration Tests\npytest -m integration\n(services must be up)"]
        end

        subgraph BUILD["Build"]
            DOCKER_BUILD["docker build\nall service images\n--cache-from registry"]
            NPM_BUILD["npm run build\nCRA production bundle"]
        end

        subgraph DEPLOY["Deploy (future)"]
            REGISTRY["Push images to\nContainer Registry"]
            K8S["kubectl apply\n(future K8s migration)"]
        end
    end

    TRIGGER --> LINT
    LINT --> TEST
    TEST --> BUILD
    BUILD --> DEPLOY

    style GHA fill:#fef9c3,stroke:#ca8a04
    style LINT fill:#dbeafe,stroke:#3b82f6
    style TEST fill:#dcfce7,stroke:#22c55e
    style BUILD fill:#f3e8ff,stroke:#9333ea
    style DEPLOY fill:#fee2e2,stroke:#ef4444
```

---

## 10.5 Deploy Script Flow

```mermaid
flowchart TD
    START(["./deploy.sh [options]"])
    
    START --> PARSE["Parse arguments\n--build | --status | --logs <svc>\n--stop | --clean"]

    PARSE --> BUILD_Q{"--build\nflag?"}
    BUILD_Q -->|"yes"| DOCKER_BUILD["docker compose build\n--no-cache (if --fresh)"]
    BUILD_Q -->|"no"| SKIP_BUILD["Skip build\nuse cached images"]

    DOCKER_BUILD & SKIP_BUILD --> UP["docker compose up -d\n(full-stack compose)"]

    UP --> WAIT["Wait for health checks\n(30s max per service)"]

    WAIT --> HEALTH_CHECK{"All services\nhealthy?"}

    HEALTH_CHECK -->|"yes"| PRINT_URLS["Print access URLs:\n  Frontend: :3004\n  Gateway:  :8004\n  Grafana:  :3100\n  RabbitMQ: :15674\n  Prometheus: :9094\n  Jaeger:  :16686"]

    HEALTH_CHECK -->|"no"| SHOW_FAILED["Show failed services\ndocker compose ps\ndocker compose logs\n(failed service)"]

    PRINT_URLS --> END(["Done"])
    SHOW_FAILED --> END

    style START fill:#3b82f6,color:#fff
    style END fill:#22c55e,color:#fff
    style HEALTH_CHECK fill:#fef9c3,stroke:#ca8a04
```

---

## 10.6 Service Startup Sequence (lifespan)

```mermaid
sequenceDiagram
    autonumber
    participant DOCKER as Docker
    participant MAIN as main.py (lifespan)
    participant DB as MySQL
    participant REDIS as Redis
    participant MQ as RabbitMQ
    participant APP as FastAPI App

    DOCKER->>MAIN: Container starts
    MAIN->>MAIN: Load config (pydantic-settings)\nread env vars

    MAIN->>DB: Create SQLAlchemy engine\nAsync connection pool
    DB-->>MAIN: Pool ready

    MAIN->>MAIN: CREATE TABLE IF NOT EXISTS\n(SQLAlchemy Base.metadata.create_all)

    MAIN->>DB: Run WEBAPI_TABLES_SQL\n(legacy WebAPI-compatible tables)\n(prediction-service only)

    MAIN->>DB: Run MIGRATION_SQL\n(idempotent ALTER TABLE scripts)

    MAIN->>DB: Run SEED_DATA_SQL\n(INSERT IGNORE reference data)

    MAIN->>REDIS: Test connection\nredis.ping()
    REDIS-->>MAIN: PONG

    MAIN->>MQ: Connect EventBus\ndeclare exchanges & queues
    MQ-->>MAIN: Connected

    MAIN->>MAIN: Start APScheduler\n(background sync jobs)

    MAIN->>APP: Mount routers\nAdd middleware\nRegister /health /metrics
    APP-->>DOCKER: Ready\n(healthcheck: GET /health/live → 200)
```
