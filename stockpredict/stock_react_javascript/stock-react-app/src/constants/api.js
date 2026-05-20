/**
 * API Configuration
 * Centralized API endpoints configuration for Microservices Architecture
 *
 * API Gateway: Traefik routes requests to microservices via /api/v2/ prefix
 * Services:
 *   - Auth Service: /api/v2/auth
 *   - Stock Data Service: /api/v2/stocks, /api/v2/companies, /api/v2/market
 *   - Portfolio Service: /api/v2/portfolio, /api/v2/alerts
 *   - Analysis Service: /api/v2/analysis, /api/v2/industries
 *   - Prediction Service: /api/v2/predict, /api/v2/models, /api/v2/solutions
 *   - AI Insights Service: /api/v2/ai
 *   - Chatbot Service: /api/v2/chatbot
 */

// Gateway base URL (Nginx/Traefik API Gateway)
// Production (nginx port 80): REACT_APP_API_URL= (empty for relative URLs)
// Development (direct Traefik): REACT_APP_API_URL=http://localhost:8004
// All requests go through nginx → Traefik → microservices
const API_GATEWAY_URL = process.env.REACT_APP_API_URL !== undefined
  ? process.env.REACT_APP_API_URL
  : 'http://localhost:8004';

// Base URLs for different services (all through API Gateway)
export const API_BASE_URLS = {
  // External services - use gateway URL if env var is empty or undefined
  CHAT_SERVICE: process.env.REACT_APP_CHAT_SERVICE_URL !== undefined
    ? process.env.REACT_APP_CHAT_SERVICE_URL
    : API_GATEWAY_URL,
  FILE_SERVICE: process.env.REACT_APP_FILE_SERVICE_URL !== undefined
    ? process.env.REACT_APP_FILE_SERVICE_URL
    : API_GATEWAY_URL,

  // All microservices accessed through Traefik API Gateway (port 8004)
  // Traefik routes based on path prefix to the appropriate backend service
  GATEWAY: API_GATEWAY_URL,
  AUTH_API: `${API_GATEWAY_URL}/stock_helper/api/v2/auth`,
  STOCK_API: `${API_GATEWAY_URL}/stock_helper/api/v2`,
  COMPANIES_API: `${API_GATEWAY_URL}/stock_helper/api/v2/companies`,
  MARKET_API: `${API_GATEWAY_URL}/stock_helper/api/v2/market`,
  PORTFOLIO_API: `${API_GATEWAY_URL}/stock_helper/api/v2/portfolio`,
  ALERTS_API: `${API_GATEWAY_URL}/stock_helper/api/v2/portfolio/alerts`,
  ANALYSIS_API: `${API_GATEWAY_URL}/stock_helper/api/v2/analysis`,
  INDUSTRIES_API: `${API_GATEWAY_URL}/stock_helper/api/v2/industries`,
  PREDICT_API: `${API_GATEWAY_URL}/stock_helper/api/v2/predict`,
  MODELS_API: `${API_GATEWAY_URL}/stock_helper/api/v2/models`,
  SOLUTIONS_API: `${API_GATEWAY_URL}/stock_helper/api/v2/solutions`,
  AI_API: `${API_GATEWAY_URL}/stock_helper/api/v2/ai`,
  CHATBOT_API: `${API_GATEWAY_URL}/stock_helper/api/v2/chat`,
  JOURNAL_API: `${API_GATEWAY_URL}/stock_helper/api/v2/journal`,
  KNOWLEDGE_QA_API: `${API_GATEWAY_URL}/stock_helper/api/v2/knowledge-qa`,
  HELPER_API: `${API_GATEWAY_URL}/stock_helper/api/v2/helper`,

  // Legacy API (fallback - Django monolith)
  LEGACY_API: `${API_GATEWAY_URL}/api/v1`
};

// API Endpoints organized by service
export const API_ENDPOINTS = {
  // ==========================================
  // AUTH SERVICE ENDPOINTS (/api/v2/auth)
  // ==========================================
  AUTH_LOGIN: `${API_BASE_URLS.AUTH_API}/login`,
  AUTH_REGISTER: `${API_BASE_URLS.AUTH_API}/register`,
  AUTH_LOGOUT: `${API_BASE_URLS.AUTH_API}/logout`,
  AUTH_REFRESH: `${API_BASE_URLS.AUTH_API}/refresh`,
  AUTH_VERIFY: `${API_BASE_URLS.AUTH_API}/verify`,
  AUTH_ME: `${API_BASE_URLS.AUTH_API}/me`,
  AUTH_CHANGE_PASSWORD: `${API_BASE_URLS.AUTH_API}/change-password`,
  AUTH_RESET_PASSWORD: `${API_BASE_URLS.AUTH_API}/reset-password`,
  AUTH_RESET_PASSWORD_CONFIRM: `${API_BASE_URLS.AUTH_API}/reset-password/confirm`,

  // ==========================================
  // STOCK DATA SERVICE ENDPOINTS (/api/v2/stocks, /api/v2/companies)
  // ==========================================
  STOCK_SEARCH: `${API_BASE_URLS.STOCK_API}/stocks/search`,
  STOCK_DETAIL: (symbol) => `${API_BASE_URLS.STOCK_API}/${symbol}`,
  STOCK_HISTORY: (symbol) => `${API_BASE_URLS.STOCK_API}/stocks/${symbol}/history`,

  COMPANIES_LIST: `${API_BASE_URLS.COMPANIES_API}`,
  COMPANIES_ALL: `${API_BASE_URLS.COMPANIES_API}/all`,
  COMPANY_PROFILE: (symbol) => `${API_BASE_URLS.COMPANIES_API}/${symbol}/profile`,
  COMPANY_FINANCIALS: (symbol) => `${API_BASE_URLS.COMPANIES_API}/${symbol}/financials`,
  COMPANY_CHARTS: (symbol) => `${API_BASE_URLS.STOCK_API}/stocks/${symbol}/history`,
  COMPANY_DIVIDENDS: (symbol) => `${API_BASE_URLS.COMPANIES_API}/${symbol}/dividends`,
  COMPANY_EVENTS: (symbol) => `${API_BASE_URLS.COMPANIES_API}/${symbol}/events`,
  COMPANY_NEWS: (symbol) => `${API_BASE_URLS.COMPANIES_API}/${symbol}/news`,

  TOP_GAINERS: `${API_BASE_URLS.COMPANIES_API}/top-gainers`,
  TOP_LOSERS: `${API_BASE_URLS.COMPANIES_API}/top-losers`,
  TOP_ACTIVES: `${API_BASE_URLS.COMPANIES_API}/top-actives`,
  PRICEBOARDS: `${API_BASE_URLS.STOCK_API}/priceboards`,

  // Market endpoints
  MARKET_INDICES: `${API_BASE_URLS.MARKET_API}/indices`,
  MARKET_INDICES_LATEST: `${API_BASE_URLS.MARKET_API}/indices/latest`,

  // Industries endpoints
  INDUSTRIES_LIST: `${API_BASE_URLS.INDUSTRIES_API}`,
  INDUSTRY_COMPANIES: (id) => `${API_BASE_URLS.INDUSTRIES_API}/${id}/companies`,

  // ==========================================
  // PORTFOLIO SERVICE ENDPOINTS (/api/v2/portfolio)
  // ==========================================
  PORTFOLIOS_LIST: `${API_BASE_URLS.PORTFOLIO_API}/portfolios`,
  PORTFOLIO_DEFAULT: `${API_BASE_URLS.PORTFOLIO_API}/portfolios/default`,
  PORTFOLIO_DETAIL: (id) => `${API_BASE_URLS.PORTFOLIO_API}/portfolios/${id}`,
  PORTFOLIO_SUMMARY: (id) => `${API_BASE_URLS.PORTFOLIO_API}/portfolios/${id}/summary`,
  PORTFOLIO_HOLDINGS: (id) => `${API_BASE_URLS.PORTFOLIO_API}/portfolios/${id}/holdings`,
  PORTFOLIO_HOLDING: (id, symbol) => `${API_BASE_URLS.PORTFOLIO_API}/portfolios/${id}/holdings/${symbol}`,
  PORTFOLIO_TRANSACTIONS: (id) => `${API_BASE_URLS.PORTFOLIO_API}/portfolios/${id}/transactions`,
  PORTFOLIO_TRANSACTIONS_BULK: (id) => `${API_BASE_URLS.PORTFOLIO_API}/portfolios/${id}/transactions/bulk`,

  // Watchlist endpoints
  WATCHLIST: `${API_BASE_URLS.PORTFOLIO_API}/watchlist`,
  WATCHLIST_REMOVE: (symbol) => `${API_BASE_URLS.PORTFOLIO_API}/watchlist/${symbol}`,

  // Notifications endpoints — backend persists portfolio.alert.triggered
  // events as Notification rows; the bell-icon widget consumes these.
  NOTIFICATIONS_LIST: `${API_BASE_URLS.PORTFOLIO_API}/notifications`,
  NOTIFICATION_MARK_READ: (id) => `${API_BASE_URLS.PORTFOLIO_API}/notifications/${id}/read`,
  NOTIFICATIONS_READ_ALL: `${API_BASE_URLS.PORTFOLIO_API}/notifications/read-all`,
  NOTIFICATION_DELETE: (id) => `${API_BASE_URLS.PORTFOLIO_API}/notifications/${id}`,

  // Web push — same Notifications loop, browser-channel.
  PUSH_VAPID_PUBLIC_KEY: `${API_BASE_URLS.PORTFOLIO_API}/push/vapid-public-key`,
  PUSH_SUBSCRIBE: `${API_BASE_URLS.PORTFOLIO_API}/push/subscribe`,
  PUSH_UNSUBSCRIBE: (endpoint) =>
    `${API_BASE_URLS.PORTFOLIO_API}/push/subscribe?endpoint=${encodeURIComponent(endpoint)}`,

  // Alerts endpoints (/api/v2/alerts)
  ALERTS_LIST: `${API_BASE_URLS.ALERTS_API}`,
  ALERT_CREATE: `${API_BASE_URLS.ALERTS_API}`,
  ALERT_DETAIL: (id) => `${API_BASE_URLS.ALERTS_API}/${id}`,
  ALERT_UPDATE: (id) => `${API_BASE_URLS.ALERTS_API}/${id}`,
  ALERT_DELETE: (id) => `${API_BASE_URLS.ALERTS_API}/${id}`,
  ALERT_TOGGLE: (id) => `${API_BASE_URLS.ALERTS_API}/${id}/toggle`,

  // ==========================================
  // ANALYSIS SERVICE ENDPOINTS (/api/v2/analysis)
  // ==========================================
  ANALYSIS_TECHNICAL: (symbol) => `${API_BASE_URLS.ANALYSIS_API}/technical/${symbol}`,
  ANALYSIS_TECHNICAL_INDICATORS: (symbol) => `${API_BASE_URLS.ANALYSIS_API}/technical/${symbol}/indicators`,
  ANALYSIS_TECHNICAL_INTRADAY: (symbol) => `${API_BASE_URLS.ANALYSIS_API}/technical/${symbol}/intraday`,
  ANALYSIS_FUNDAMENTAL: (symbol) => `${API_BASE_URLS.ANALYSIS_API}/fundamental/${symbol}`,
  ANALYSIS_FUNDAMENTAL_STATEMENTS: (symbol) => `${API_BASE_URLS.ANALYSIS_API}/fundamental/${symbol}/statements`,

  // Financial Reports endpoints (via stock-data-service)
  FINANCIAL_INCOME_STATEMENT: (symbol) => `${API_BASE_URLS.COMPANIES_API}/${symbol}/financials/income-statement`,
  FINANCIAL_BALANCE_SHEET: (symbol) => `${API_BASE_URLS.COMPANIES_API}/${symbol}/financials/balance-sheet`,
  FINANCIAL_CASH_FLOW: (symbol) => `${API_BASE_URLS.COMPANIES_API}/${symbol}/financials/cash-flow`,
  FINANCIAL_RATIO: (symbol) => `${API_BASE_URLS.COMPANIES_API}/${symbol}/financials/ratios`,
  ANALYSIS_COMPARE: `${API_BASE_URLS.ANALYSIS_API}/compare`,
  ANALYSIS_SCREENER: `${API_BASE_URLS.ANALYSIS_API}/screener`,
  ANALYSIS_SCREENER_CONFIGS: `${API_BASE_URLS.ANALYSIS_API}/screener/configs`,
  ANALYSIS_FILTERS: `${API_BASE_URLS.ANALYSIS_API}/filters`,
  ANALYSIS_SIGNALS: `${API_BASE_URLS.ANALYSIS_API}/signals`,
  ANALYSIS_SECTORS: `${API_BASE_URLS.ANALYSIS_API}/sectors`,
  ANALYSIS_INDUSTRY: (id) => `${API_BASE_URLS.ANALYSIS_API}/industries/${id}/analysis`,

  // ==========================================
  // PREDICTION SERVICE ENDPOINTS (/api/v2/predict, /api/v2/models, /api/v2/solutions)
  // ==========================================
  // Predict endpoints
  PREDICT: `${API_BASE_URLS.PREDICT_API}/predict`,
  PREDICT_SYMBOL: (symbol) => `${API_BASE_URLS.PREDICT_API}/predict/${symbol}`,
  PREDICT_BULK: `${API_BASE_URLS.PREDICT_API}/predict/bulk`,
  PREDICT_BACKTEST: `${API_BASE_URLS.PREDICT_API}/backtest`,
  PREDICT_COMPARE: `${API_BASE_URLS.PREDICT_API}/compare`,
  PREDICT_SUPPORTED_MODELS: `${API_BASE_URLS.PREDICT_API}/supported-models`,

  // Model endpoints
  MODELS_LIST: `${API_BASE_URLS.MODELS_API}`,
  MODEL_DETAIL: (id) => `${API_BASE_URLS.MODELS_API}/${id}`,
  MODEL_CREATE: `${API_BASE_URLS.MODELS_API}`,
  MODEL_UPDATE: (id) => `${API_BASE_URLS.MODELS_API}/${id}`,
  MODEL_DELETE: (id) => `${API_BASE_URLS.MODELS_API}/${id}`,
  MODEL_FEATURES: (id) => `${API_BASE_URLS.MODELS_API}/${id}/features`,
  MODEL_TRAINING_LOGS: (id) => `${API_BASE_URLS.MODELS_API}/${id}/training-logs`,
  MODEL_TRAIN: `${API_BASE_URLS.MODELS_API}/train`,
  MODEL_PARAMETERS: `${API_BASE_URLS.MODELS_API}/parameters`,
  MODEL_PARAM_OPTIONS: `${API_BASE_URLS.MODELS_API}/params/options`,
  MODEL_TYPES: `${API_BASE_URLS.MODELS_API}/types`,
  MODELS_HEALTH: `${API_BASE_URLS.PREDICT_API}/health/models`,

  // Solution endpoints
  SOLUTIONS_LIST: `${API_BASE_URLS.SOLUTIONS_API}`,
  SOLUTION_DETAIL: (id) => `${API_BASE_URLS.SOLUTIONS_API}/${id}`,
  SOLUTION_CREATE: `${API_BASE_URLS.SOLUTIONS_API}`,
  SOLUTION_UPDATE: (id) => `${API_BASE_URLS.SOLUTIONS_API}/${id}`,
  SOLUTION_DELETE: (id) => `${API_BASE_URLS.SOLUTIONS_API}/${id}`,
  SOLUTION_TICKERS: `${API_BASE_URLS.SOLUTIONS_API}/tickers`,
  SOLUTION_INDICATORS: (id) => `${API_BASE_URLS.SOLUTIONS_API}/${id}/indicators`,
  SOLUTION_INDICATORS_SET: (id) => `${API_BASE_URLS.SOLUTIONS_API}/${id}/indicators/set`,

  // Time Series endpoints (under predict)
  TIME_SERIES_LIST: `${API_BASE_URLS.PREDICT_API}/time_series`,
  TIME_SERIES_DETAIL: (id) => `${API_BASE_URLS.PREDICT_API}/time_series/${id}`,
  TIME_SERIES_CREATE: `${API_BASE_URLS.PREDICT_API}/time_series`,
  TIME_SERIES_UPDATE: (id) => `${API_BASE_URLS.PREDICT_API}/time_series/${id}`,
  TIME_SERIES_DELETE: (id) => `${API_BASE_URLS.PREDICT_API}/time_series/${id}`,
  TIME_SERIES_BY_IDS: `${API_BASE_URLS.PREDICT_API}/time_series/by_ids`,
  TIME_SERIES_BATCH_UPDATE: `${API_BASE_URLS.PREDICT_API}/time_series/batch_update`,
  TIME_SERIES_CATEGORIES: `${API_BASE_URLS.PREDICT_API}/time_series/categories`,

  // Solution training/prediction endpoints
  SOLUTION_TRAIN: `${API_BASE_URLS.SOLUTIONS_API}/train`,
  SOLUTION_PREDICT: `${API_BASE_URLS.SOLUTIONS_API}/predict`,
  SOLUTION_TRAINING_STATUS: (id) => `${API_BASE_URLS.SOLUTIONS_API}/${id}/training-status`,
  SOLUTION_COVARIATES: `${API_BASE_URLS.SOLUTIONS_API}/covariates`,
  SOLUTION_CALCULATE_DATE_RANGE: `${API_BASE_URLS.SOLUTIONS_API}/calculate-date-range`,

  // Simulation endpoints
  SIMULATION_MODELS: `${API_BASE_URLS.PREDICT_API}/simulation/models`,
  SIMULATION_TRAINED_SOLUTIONS: `${API_BASE_URLS.PREDICT_API}/simulation/trained-solutions`,
  SIMULATION_RUN: `${API_BASE_URLS.PREDICT_API}/simulation/run`,

  // Model endpoints (additional)
  MODELS_ALL: `${API_BASE_URLS.MODELS_API}/all`,
  MODEL_BY_TYPE: (type) => `${API_BASE_URLS.MODELS_API}/${type}`,

  // Company historical data
  COMPANY_HISTORICAL_DATA: (symbol, startDate, endDate) =>
    `${API_BASE_URLS.COMPANIES_API}/${symbol}/historical-data?start_date=${startDate}&end_date=${endDate}`,

  // Technical Indicators endpoints (under predict)
  INDICATORS_LIST: `${API_BASE_URLS.PREDICT_API}/indicators`,
  INDICATORS_BY_TYPE: (type) => `${API_BASE_URLS.PREDICT_API}/indicators/type/${type}`,
  INDICATOR_DETAIL: (id) => `${API_BASE_URLS.PREDICT_API}/indicators/${id}`,
  INDICATOR_CALCULATE: `${API_BASE_URLS.PREDICT_API}/indicators/calculate`,
  INDICATOR_CREATE: `${API_BASE_URLS.PREDICT_API}/indicators`,
  INDICATOR_UPDATE: (id) => `${API_BASE_URLS.PREDICT_API}/indicators/${id}`,
  INDICATOR_DELETE: (id) => `${API_BASE_URLS.PREDICT_API}/indicators/${id}`,

  // ==========================================
  // AI INSIGHTS SERVICE ENDPOINTS (/api/v2/ai)
  // ==========================================
  AI_INSIGHT: `${API_BASE_URLS.AI_API}/insight`,
  AI_INSIGHT_SYMBOL: (symbol) => `${API_BASE_URLS.AI_API}/insight/${symbol}`,
  AI_COMPARE: `${API_BASE_URLS.AI_API}/compare`,
  AI_NEWS_ANALYSIS: `${API_BASE_URLS.AI_API}/news-analysis`,
  AI_ASK: `${API_BASE_URLS.AI_API}/ask`,
  AI_MARKET_OVERVIEW: `${API_BASE_URLS.AI_API}/market-overview`,
  AI_BATCH: `${API_BASE_URLS.AI_API}/batch`,
  AI_TRENDING: `${API_BASE_URLS.AI_API}/trending`,
  AI_RECOMMENDATIONS: `${API_BASE_URLS.AI_API}/recommendations`,
  AI_PORTFOLIO_INSIGHTS: `${API_BASE_URLS.AI_API}/portfolio-insight`,
  AI_SECTORS: `${API_BASE_URLS.AI_API}/sectors`,
  AI_CAPABILITIES: `${API_BASE_URLS.AI_API}/capabilities`,
  AI_INDICATORS_AVAILABLE: `${API_BASE_URLS.AI_API}/indicators/available`,
  AI_INDICATORS_DATA: `${API_BASE_URLS.AI_API}/indicators/data`,

  // Agent endpoints (under AI)
  AGENTS_LIST: `${API_BASE_URLS.AI_API}/agents`,
  AGENT_GET: `${API_BASE_URLS.AI_API}/agent`,
  AGENT_ML: `${API_BASE_URLS.AI_API}/ml_agent`,

  // ==========================================
  // CHATBOT SERVICE ENDPOINTS (/api/v2/chatbot)
  // ==========================================
  CHATBOT_CHAT: `${API_BASE_URLS.CHATBOT_API}/chat`,
  CHATBOT_HISTORY: (sessionId) => `${API_BASE_URLS.CHATBOT_API}/history/${sessionId}`,
  CHATBOT_SESSION_CLEAR: (sessionId) => `${API_BASE_URLS.CHATBOT_API}/session/${sessionId}`,
  CHATBOT_SUGGESTIONS: `${API_BASE_URLS.CHATBOT_API}/suggestions`,
  CHATBOT_FEEDBACK: `${API_BASE_URLS.CHATBOT_API}/feedback`,
  CHATBOT_EXPORT: (id) => `${API_BASE_URLS.CHATBOT_API}/history/${id}/export`,
  CHATBOT_INTENTS: `${API_BASE_URLS.CHATBOT_API}/intents`,
  CHATBOT_STATS: `${API_BASE_URLS.CHATBOT_API}/stats`,
  CHATBOT_CAPABILITIES: `${API_BASE_URLS.CHATBOT_API}/capabilities`,
  CHATBOT_HEALTH: `${API_BASE_URLS.CHATBOT_API}/health`,
  CHATBOT_WS: (sessionId) => `ws://${API_GATEWAY_URL.replace(/^https?:\/\//, '')}/api/v2/chatbot/ws/${sessionId}`,

  // ==========================================
  // JOURNAL SERVICE ENDPOINTS (/api/v2/journal)
  // ==========================================
  JOURNAL_ACCOUNTS: `${API_BASE_URLS.JOURNAL_API}/accounts`,
  JOURNAL_ACCOUNT: (id) => `${API_BASE_URLS.JOURNAL_API}/accounts/${id}`,
  JOURNAL_ACCOUNT_RULES: (id) => `${API_BASE_URLS.JOURNAL_API}/accounts/${id}/rules`,
  JOURNAL_ACCOUNT_RULE: (accountId, ruleId) => `${API_BASE_URLS.JOURNAL_API}/accounts/${accountId}/rules/${ruleId}`,
  JOURNAL_ACCOUNT_TRADES: (id) => `${API_BASE_URLS.JOURNAL_API}/accounts/${id}/trades`,
  JOURNAL_TRADE: (accountId, tradeId) => `${API_BASE_URLS.JOURNAL_API}/accounts/${accountId}/trades/${tradeId}`,
  JOURNAL_TRADE_CLOSE: (accountId, tradeId) => `${API_BASE_URLS.JOURNAL_API}/accounts/${accountId}/trades/${tradeId}/close`,
  JOURNAL_TRADE_STOP: (accountId, tradeId) => `${API_BASE_URLS.JOURNAL_API}/accounts/${accountId}/trades/${tradeId}/stop`,
  JOURNAL_ACCOUNT_RISK: (id) => `${API_BASE_URLS.JOURNAL_API}/accounts/${id}/risk`,
  JOURNAL_TRADE_DIARY: (tradeId) => `${API_BASE_URLS.JOURNAL_API}/trades/${tradeId}/diary`,
  JOURNAL_DIARY_CHARTS: (diaryId) => `${API_BASE_URLS.JOURNAL_API}/diary/${diaryId}/charts`,
  JOURNAL_DIARY_CHART_DELETE: (chartId) => `${API_BASE_URLS.JOURNAL_API}/diary/charts/${chartId}`,
  JOURNAL_DAILY_PLANS: (id) => `${API_BASE_URLS.JOURNAL_API}/accounts/${id}/plans`,
  JOURNAL_DAILY_PLAN: (accountId, planId) => `${API_BASE_URLS.JOURNAL_API}/accounts/${accountId}/plans/${planId}`,
  JOURNAL_WEEKLY_REVIEWS: (id) => `${API_BASE_URLS.JOURNAL_API}/accounts/${id}/reviews`,
  JOURNAL_WEEKLY_REVIEW: (accountId, reviewId) => `${API_BASE_URLS.JOURNAL_API}/accounts/${accountId}/reviews/${reviewId}`,
  JOURNAL_WEEKLY_REVIEW_RECALC: (accountId, reviewId) => `${API_BASE_URLS.JOURNAL_API}/accounts/${accountId}/reviews/${reviewId}/recalculate`,
  JOURNAL_DASHBOARD: (id) => `${API_BASE_URLS.JOURNAL_API}/accounts/${id}/dashboard`,
  JOURNAL_EQUITY_SNAPSHOTS: (id) => `${API_BASE_URLS.JOURNAL_API}/accounts/${id}/equity`,
  JOURNAL_INFO: `${API_BASE_URLS.JOURNAL_API}/info`,

  // ==========================================
  // KNOWLEDGE QA SERVICE ENDPOINTS (/api/v2/knowledge-qa)
  // ==========================================
  KNOWLEDGE_QA_CHAT: `${API_BASE_URLS.KNOWLEDGE_QA_API}/chat`,
  KNOWLEDGE_QA_HISTORY: (sessionId) => `${API_BASE_URLS.KNOWLEDGE_QA_API}/chat/history/${sessionId}`,
  KNOWLEDGE_QA_CLEAR: (sessionId) => `${API_BASE_URLS.KNOWLEDGE_QA_API}/chat/clear/${sessionId}`,
  KNOWLEDGE_QA_SEARCH: `${API_BASE_URLS.KNOWLEDGE_QA_API}/search`,
  KNOWLEDGE_QA_STATS: `${API_BASE_URLS.KNOWLEDGE_QA_API}/stats`,
  KNOWLEDGE_QA_HEALTH: `${API_BASE_URLS.KNOWLEDGE_QA_API}/health`,

  // ==========================================
  // FILE SERVICE ENDPOINTS (external service)
  // ==========================================
  FILE_LIST: `${API_BASE_URLS.FILE_SERVICE}/files`,
  FILE_UPLOAD: `${API_BASE_URLS.FILE_SERVICE}/upload`,
  FILE_DELETE: `${API_BASE_URLS.FILE_SERVICE}/delete`,
  FILE_PROCESS: `${API_BASE_URLS.FILE_SERVICE}/process`,

  // Chat service (external)
  CHAT_QUERY: `${API_BASE_URLS.CHAT_SERVICE}/query`,

  // ==========================================
  // LEGACY ENDPOINTS (backward compatibility)
  // These map old endpoint patterns to new microservices
  // ==========================================
  // Legacy aliases for gradual migration
  STOCK_DATA: `${API_BASE_URLS.STOCK_API}`,
  STOCK_ANALYSIS: `${API_BASE_URLS.ANALYSIS_API}`,

  // Old chatbot endpoints (mapped to new)
  CHATBOT_ASK: `${API_BASE_URLS.CHATBOT_API}/chat`,
  CHATBOT_CATEGORIES: `${API_BASE_URLS.CHATBOT_API}/suggestions`,

  // Old model endpoints (mapped to new)
  MODEL_LIST: `${API_BASE_URLS.MODELS_API}`,

  // Old solution endpoints (mapped to new)
  SOLUTION_LIST: `${API_BASE_URLS.SOLUTIONS_API}`,

  // ==========================================
  // DECISION HELPER SERVICE ENDPOINTS (/api/v2/helper)
  // F-030 — Phase D
  // ==========================================
  HELPER_RECOMMEND: `${API_BASE_URLS.HELPER_API}/recommend`,
  HELPER_SIGNAL_ANALYSIS: `${API_BASE_URLS.HELPER_API}/signal-analysis`,
  HELPER_POSITION: (ticker) => `${API_BASE_URLS.HELPER_API}/positions/${ticker}`,
  HELPER_RISK_PREFS: `${API_BASE_URLS.HELPER_API}/risk-prefs`,
  HELPER_CAPABILITIES: `${API_BASE_URLS.HELPER_API}/capabilities`,
  HELPER_BACKTEST: `${API_BASE_URLS.HELPER_API}/backtest`,
  HELPER_DISCIPLINE_SUMMARY: `${API_BASE_URLS.HELPER_API}/discipline/summary`,
  HELPER_VALIDATE_PLAN: `${API_BASE_URLS.HELPER_API}/discipline/validate-plan`,
  // F-070..F-073
  HELPER_WATCHLIST: `${API_BASE_URLS.HELPER_API}/watchlist`,
  HELPER_WATCHLIST_ITEM: (ticker) => `${API_BASE_URLS.HELPER_API}/watchlist/${ticker}`,
  HELPER_WATCHLIST_RUN_ALL: `${API_BASE_URLS.HELPER_API}/watchlist/run-all`,
  HELPER_SCHEDULED_RUNS: `${API_BASE_URLS.HELPER_API}/scheduled-runs`,
  // F-080..F-083
  HELPER_ALERTS: `${API_BASE_URLS.HELPER_API}/alerts`,
  HELPER_ALERTS_STREAM: `${API_BASE_URLS.HELPER_API}/alerts/stream`,
  // F-100..F-103 — Pattern overlay (ai-insights-service)
  AI_PATTERNS: (symbol) => `${API_BASE_URLS.AI_API}/insights/patterns/${symbol}`,
  // F-120..F-123 — Multi-ticker scanner
  HELPER_SCAN: `${API_BASE_URLS.HELPER_API}/scan`,
  // F-130..F-133 — Performance analytics
  HELPER_ANALYTICS: `${API_BASE_URLS.HELPER_API}/analytics`,
  // F-150..F-153 — Open positions dashboard
  HELPER_POSITIONS_LIST: `${API_BASE_URLS.HELPER_API}/positions`,
  HELPER_POSITION_STOP: (ticker) => `${API_BASE_URLS.HELPER_API}/positions/${ticker}/stop`,
  // F-160..F-163 — Trade outcome tagging
  HELPER_OUTCOMES: `${API_BASE_URLS.HELPER_API}/outcomes`,
};

// HTTP Status Codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500
};

// Request timeout in milliseconds
export const REQUEST_TIMEOUT = 30000;