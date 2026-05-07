# 07 — Frontend Architecture

## 7.1 React Application Structure

```mermaid
flowchart TD
    subgraph ENTRY["Entry Points"]
        IDX["index.js\nReactDOM.createRoot"]
        APP["App.js\nRoot component\nReact Router v6"]
    end

    subgraph LAYOUT["Layout Layer"]
        MAIN_LAYOUT["MainLayout.js\nNavbar + Sidebar\n+ Content Area"]
        AUTH_LAYOUT["AuthLayout.js\nCentered auth forms"]
    end

    subgraph PAGES["Page Components (Route-level)"]
        direction TB
        P_STOCKS["Stocks.js\nStock search & list"]
        P_COMPANY["Company/\nCompany detail\nFinancials · News · Events"]
        P_ANALYSIS["TechnicalAnalysis.js\nFundamentalAnalysis.js"]
        P_PREDICT["Predict.js\nSimulationDashboard.js"]
        P_MODELS["models/\nML model management"]
        P_SOLUTIONS["Solutions/\nSolution builder"]
        P_PORTFOLIO["Portfolio/\nHoldings · Transactions\nAlerts · Performance"]
        P_JOURNAL["Journal/\nTrades · Plans · Reviews"]
        P_AI["AIInsights.js\nAI market analysis"]
        P_CHAT["ChatbotAgent.js\nConversational AI"]
        P_KQA["KnowledgeQAChat.js\nGraph RAG Q&A"]
        P_PRICEBOARD["PriceBoard.js\nVN30 live board"]
        P_WATCHLIST["Watchlist.js\nUser watchlists"]
        P_AGENT["Agent.js\nAI Agent panel"]
        P_INDICATORS["Indicators/\nCustom indicators"]
        P_TIMESERIES["TimeSeries/\nTime series mgmt"]
        P_MARKET["MarketMovers/\nTop gainers/losers"]
        P_CALC["PositionCalculator.js\nRisk/position sizing"]
    end

    subgraph SHARED_COMP["Shared Components"]
        UI["ui/\nButton · Card · Modal\nTable · Chart · Badge"]
        COMMON["common/\nLoadingSpinner\nErrorBoundary\nConfirmDialog\nPagination"]
        AUTH_COMP["Auth/\nLoginForm · RegisterForm\nProtectedRoute"]
    end

    subgraph STATE["State Management"]
        CTX_AUTH["AuthContext\nuser, token\nlogin() logout()"]
        CTX_PORTFOLIO["PortfolioContext\ncurrent portfolio\nholdings cache"]
        CTX_THEME["ThemeContext\nlight/dark mode"]
        LOCAL_STG["localStorage\nJWT tokens\nuser preferences"]
    end

    subgraph HOOKS["Custom Hooks"]
        H_AUTH["useAuth()\ncurrent user, role\ntoken management"]
        H_API["useApi()\nloading, error, data\ngeneric fetch hook"]
        H_STOCKS["useStockData()\nprice polling\n(2-5s interval)"]
        H_PORTFOLIO["usePortfolio()\nportfolio state\nrefresh triggers"]
    end

    IDX --> APP
    APP --> MAIN_LAYOUT & AUTH_LAYOUT
    MAIN_LAYOUT --> PAGES
    PAGES --> SHARED_COMP
    PAGES --> HOOKS
    HOOKS --> STATE
    STATE --> LOCAL_STG
    AUTH_COMP --> CTX_AUTH

    style ENTRY fill:#dbeafe,stroke:#3b82f6
    style PAGES fill:#dcfce7,stroke:#22c55e
    style STATE fill:#f3e8ff,stroke:#9333ea
    style HOOKS fill:#fef9c3,stroke:#ca8a04
```

---

## 7.2 Service Layer Architecture

```mermaid
flowchart TD
    subgraph COMPONENTS["React Components\n(Consumers)"]
        C1["TechnicalAnalysis.js"]
        C2["AIInsights.js"]
        C3["Portfolio.js"]
        C4["ChatbotAgent.js"]
    end

    subgraph SERVICE_LAYER["Service Layer (/src/services/)"]
        HTTP["httpClient.js\nBase HTTP client\n- Fetch wrapper\n- Auth header injection\n- Error normalization\n- Response parsing"]
        
        API["api.js\nMain API service\n(covers all endpoints)"]
        
        COMP_SVC["companyService.js\ngetCompany(symbol)\ngetFinancials(symbol)\ngetNews(symbol)"]
        PORT_SVC["portfolioService.js\ngetPortfolios()\ncreatePortfolio(data)\naddHolding(portfolioId, data)"]
        MODEL_SVC["modelService.js\ngetModels()\ntrainModel(config)\ngetModelStatus(id)"]
        SOL_SVC["solutionService.js\ngetSolutions()\ncreateSolution(data)\nrunPrediction(id, symbol)"]
        IND_SVC["indicatorService.js\ngetIndicators()\ncalculate(symbol, type)"]
        TS_SVC["timeSeriesService.js\ngetTimeSeries(symbol)\ncreateTimeSeries(data)"]
        JOUR_SVC["journalService.js\ngetAccounts()\ncreateTrade(data)\ngetMetrics(accountId)"]
        QA_SVC["knowledgeQAService.js\nask(question, sessionId)\nsearch(query)\ngetStats()"]
        CHAT_SVC["chatbotAgentService.js\nsendMessage(text, sessionId)\ngetHistory(sessionId)\ngetSuggestions()"]
        FILE_SVC["fileService.js\nuploadChart(file)\ndownloadReport(id)"]
    end

    subgraph CONSTANTS["Constants (/src/constants/)"]
        API_CONST["api.js\nAPI_BASE_URL\nAPI_ENDPOINTS\nall URL constants"]
    end

    C1 & C2 & C3 & C4 --> API & COMP_SVC & PORT_SVC & MODEL_SVC
    C4 --> CHAT_SVC
    C2 --> JOUR_SVC

    API --> HTTP
    COMP_SVC --> HTTP
    PORT_SVC --> HTTP
    MODEL_SVC --> HTTP
    SOL_SVC --> HTTP
    IND_SVC --> HTTP
    TS_SVC --> HTTP
    JOUR_SVC --> HTTP
    QA_SVC --> HTTP
    CHAT_SVC --> HTTP
    FILE_SVC --> HTTP

    HTTP --> API_CONST

    style SERVICE_LAYER fill:#fef9c3,stroke:#ca8a04
    style COMPONENTS fill:#dbeafe,stroke:#3b82f6
    style CONSTANTS fill:#dcfce7,stroke:#22c55e
```

---

## 7.3 Route Map

```mermaid
flowchart TD
    ROOT["/stock-app (homepage)"]

    ROOT --> AUTH_R["/stock-app/auth/*"]
    AUTH_R --> LOGIN["/login"]
    AUTH_R --> REGISTER["/register"]

    ROOT --> MARKET_R["/market/*"]
    MARKET_R --> PRICEBOARD["/priceboard\nVN30 live board"]
    MARKET_R --> MOVERS["/movers\nTop gainers/losers"]
    MARKET_R --> INDICES["/indices\nMarket indices"]

    ROOT --> STOCKS_R["/stocks/*"]
    STOCKS_R --> STOCK_LIST["/stocks\nSearch & browse"]
    STOCKS_R --> STOCK_DETAIL["/stocks/:symbol\nCompany detail"]
    STOCKS_R --> TECHNICAL["/stocks/:symbol/technical"]
    STOCKS_R --> FUNDAMENTAL["/stocks/:symbol/fundamental"]

    ROOT --> PORTFOLIO_R["/portfolio/*"]
    PORTFOLIO_R --> PORT_LIST["/portfolio\nMy portfolios"]
    PORTFOLIO_R --> PORT_DETAIL["/portfolio/:id"]
    PORTFOLIO_R --> WATCHLIST["/watchlist"]
    PORTFOLIO_R --> ALERTS["/alerts"]
    PORTFOLIO_R --> CALC["/position-calculator"]

    ROOT --> AI_R["/ai/*"]
    AI_R --> AI_INSIGHTS["/ai/insights\nMarket AI overview"]
    AI_R --> CHATBOT["/ai/chat\nConversational AI"]
    AI_R --> KQA["/ai/knowledge-qa\nGraph RAG Q&A"]
    AI_R --> AGENT["/ai/agent\nAI Agent panel"]

    ROOT --> PRED_R["/predictions/*"]
    PRED_R --> PREDICT["/predict\nRun prediction"]
    PRED_R --> MODELS["/models\nModel management"]
    PRED_R --> SOLUTIONS["/solutions\nSolution builder"]
    PRED_R --> SIMULATION["/simulation\nBacktest / simulation"]
    PRED_R --> INDICATORS["/indicators\nCustom indicators"]
    PRED_R --> TIMESERIES["/time-series\nTime series data"]

    ROOT --> JOURNAL_R["/journal/*"]
    JOURNAL_R --> JOUR_HOME["/journal\nDashboard"]
    JOURNAL_R --> TRADES["/journal/trades"]
    JOURNAL_R --> PLANS["/journal/plans"]
    JOURNAL_R --> REVIEWS["/journal/reviews"]
    JOURNAL_R --> EQUITY["/journal/equity-curve"]

    style ROOT fill:#3b82f6,color:#fff
    style AUTH_R fill:#fee2e2,stroke:#ef4444
    style MARKET_R fill:#dcfce7,stroke:#22c55e
    style STOCKS_R fill:#dbeafe,stroke:#3b82f6
    style PORTFOLIO_R fill:#fef9c3,stroke:#ca8a04
    style AI_R fill:#f3e8ff,stroke:#9333ea
    style PRED_R fill:#fff7ed,stroke:#ea580c
    style JOURNAL_R fill:#f0fdf4,stroke:#15803d
```

---

## 7.4 Data Flow — Component ↔ API

```mermaid
sequenceDiagram
    autonumber
    participant USER as User Interaction
    participant COMP as React Component
    participant HOOK as Custom Hook\n(useApi / useStockData)
    participant CTX as Context (AuthContext)
    participant SVC as Service Layer\n(api.js / *Service.js)
    participant HTTP as httpClient.js
    participant GW as Traefik Gateway

    USER->>COMP: Click "Load Stock Analysis"
    COMP->>HOOK: call hook with symbol
    HOOK->>HOOK: set loading=true
    HOOK->>SVC: service.getAnalysis(symbol)
    SVC->>SVC: build URL from API_ENDPOINTS
    SVC->>HTTP: http.get(url)
    HTTP->>CTX: getToken() from AuthContext
    CTX-->>HTTP: Bearer <jwt>
    HTTP->>GW: GET /stock_helper/api/v2/analysis/technical/VNM\nAuthorization: Bearer <jwt>
    GW-->>HTTP: 200 {rsi: 62, macd: ..., signal: BULLISH}
    HTTP->>HTTP: parse JSON, normalize errors
    HTTP-->>SVC: data object
    SVC-->>HOOK: data
    HOOK->>HOOK: set data=result, loading=false
    HOOK-->>COMP: {data, loading, error}
    COMP->>COMP: re-render with analysis data
    COMP-->>USER: Display chart & signals
```

---

## 7.5 Authentication State Flow

```mermaid
stateDiagram-v2
    [*] --> UNAUTHENTICATED : App loads

    UNAUTHENTICATED --> UNAUTHENTICATED : Access protected route\n→ redirect to /login

    UNAUTHENTICATED --> AUTHENTICATING : User submits login form

    AUTHENTICATING --> AUTHENTICATED : POST /auth/login → 200\nStore JWT + refresh token\nin localStorage

    AUTHENTICATING --> UNAUTHENTICATED : 401 Invalid credentials\nshow error

    AUTHENTICATED --> AUTHENTICATED : API call with valid JWT\n→ 200 response

    AUTHENTICATED --> REFRESHING : API call → 401 JWT expired\nautomatically trigger refresh

    REFRESHING --> AUTHENTICATED : POST /auth/refresh → 200\nnew JWT stored

    REFRESHING --> UNAUTHENTICATED : Refresh token expired\nforce logout\nclear localStorage

    AUTHENTICATED --> UNAUTHENTICATED : User clicks logout\nclear localStorage\nredirect to /login

    note right of AUTHENTICATED
        JWT payload decoded:
        - user_id
        - role (user/admin/premium)
        - exp timestamp
        Stored in AuthContext
    end note
```

---

## 7.6 Component Hierarchy (Key Pages)

```mermaid
graph TD
    subgraph AI_PAGE["AIInsights Page"]
        AI["AIInsights.js\n(page)"]
        AI --> OVERVIEW["MarketOverviewCard\nGPT summary"]
        AI --> TRENDING["TrendingStocksPanel\nAI trending picks"]
        AI --> SECTORS["SectorAnalysisChart\nheatmap by sector"]
        AI --> SENTIMENT["SentimentMeter\nbull/bear indicator"]
        AI --> ASK_AI["AskAIPanel\nfree-form question input"]
    end

    subgraph PORTFOLIO_PAGE["Portfolio Page"]
        PORT["Portfolio.js\n(page)"]
        PORT --> PERF_CARD["PerformanceCard\ntotal value, P&L"]
        PORT --> HOLD_TABLE["HoldingsTable\nsymbol, qty, value, P&L"]
        PORT --> TXN_LIST["TransactionList\nbuy/sell history"]
        PORT --> ALERT_WIDGET["AlertsWidget\nactive price alerts"]
        PORT --> ALLOC_CHART["AllocationChart\npie chart by sector"]
    end

    subgraph STOCK_PAGE["Stock Detail Page"]
        STK["StockDetail.js\n(page)"]
        STK --> PRICE_HEADER["PriceHeader\nlive price + change"]
        STK --> CHART["PriceChart\ncandlestick + volume"]
        STK --> TECH_PANEL["TechnicalPanel\nRSI · MACD · BB signals"]
        STK --> AI_INSIGHT_CARD["AIInsightCard\nLLM-generated analysis"]
        STK --> NEWS_FEED["NewsFeed\ncompany news"]
        STK --> FINANCIALS_TAB["FinancialsTab\nIS · BS · CF"]
    end
```
