"""Generate the StockPredict project roadmap workbook.

Run once: `python3 build_roadmap_excel.py` — produces ROADMAP.xlsx in the repo root.
The script is idempotent; re-run to regenerate after status edits in this file.
"""
from __future__ import annotations
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.comments import Comment

OUT = "/home/home/all_projects/stockpredict/ROADMAP.xlsx"

# ---- Style helpers ---------------------------------------------------------
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
TITLE_FONT = Font(name="Calibri", bold=True, size=16, color="1F4E78")
SUBTITLE_FONT = Font(name="Calibri", italic=True, size=10, color="595959")

STATUS_FILLS = {
    "Done":         PatternFill("solid", fgColor="C6EFCE"),
    "In Progress":  PatternFill("solid", fgColor="FFEB9C"),
    "Partial":      PatternFill("solid", fgColor="FFEB9C"),
    "Stub":         PatternFill("solid", fgColor="FFC7CE"),
    "Planned":      PatternFill("solid", fgColor="DDEBF7"),
    "Not Started":  PatternFill("solid", fgColor="F2F2F2"),
    "Blocked":      PatternFill("solid", fgColor="FFC7CE"),
    "Tech Debt":    PatternFill("solid", fgColor="FCE4D6"),
}


def style_header_row(ws, row, last_col):
    for c in range(1, last_col + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        cell.border = BORDER


def write_rows(ws, headers, rows, header_row=1, freeze=True):
    for i, h in enumerate(headers, 1):
        ws.cell(row=header_row, column=i, value=h)
    style_header_row(ws, header_row, len(headers))
    for r, row in enumerate(rows, start=header_row + 1):
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = BORDER
    if freeze:
        ws.freeze_panes = ws.cell(row=header_row + 1, column=1)


def autosize(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def add_status_conditional(ws, status_col_letter, first_data_row, last_data_row):
    rng = f"{status_col_letter}{first_data_row}:{status_col_letter}{last_data_row}"
    for status, fill in STATUS_FILLS.items():
        ws.conditional_formatting.add(
            rng,
            CellIsRule(operator="equal", formula=[f'"{status}"'], fill=fill),
        )


# ---- Workbook --------------------------------------------------------------
wb = Workbook()

# =============================================================================
# Sheet 1: Overview
# =============================================================================
ws = wb.active
ws.title = "Overview"

ws["A1"] = "StockPredict — Project Roadmap & Status"
ws["A1"].font = TITLE_FONT
ws.merge_cells("A1:F1")

ws["A2"] = "Snapshot of features, current status, and what's next. Update the Status column to keep yourself oriented across sessions."
ws["A2"].font = SUBTITLE_FONT
ws.merge_cells("A2:F2")

ws["A4"] = "Project"
ws["B4"] = "Vietnamese stock-market platform: portfolio tracking, ML price prediction, technical/fundamental analysis, AI chatbot, trading journal, knowledge-base Q&A."
ws["A5"] = "Architecture"
ws["B5"] = "9 FastAPI microservices behind Traefik (port 8004) + React 19 frontend (CRA) + MySQL + Redis + RabbitMQ + Prometheus/Grafana/Jaeger + Neo4j + Ollama."
ws["A6"] = "Migration story"
ws["B6"] = "Strangler-fig migration from a Django monolith. Phase 2 (build microservices) is largely DONE. Phase 3 (shadow/cutover/decommission) is partially done."
ws["A7"] = "Repo layout"
ws["B7"] = "stock_microservices/ (backend)  |  stock_react_javascript/stock-react-app/ (frontend)  |  deploy.sh + docker-compose.full-stack.yml (full stack)"
ws["A8"] = "Source of truth for routing"
ws["B8"] = "stock_microservices/docker-compose.yml (Traefik labels) and stock_react_javascript/stock-react-app/src/constants/api.js"
for r in range(4, 9):
    ws.cell(row=r, column=1).font = Font(bold=True)
    ws.cell(row=r, column=1).alignment = Alignment(vertical="top")
    ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")
ws.row_dimensions[6].height = 32
ws.row_dimensions[7].height = 32

# Status counts (computed from Feature Inventory tab via formulas)
ws["A10"] = "Status counts (auto-updated from Feature Inventory sheet)"
ws["A10"].font = Font(bold=True, size=12)
ws.merge_cells("A10:F10")

counts = [
    ("Done",        '=COUNTIF(\'Feature Inventory\'!E:E,"Done")'),
    ("In Progress", '=COUNTIF(\'Feature Inventory\'!E:E,"In Progress")'),
    ("Partial",     '=COUNTIF(\'Feature Inventory\'!E:E,"Partial")'),
    ("Stub",        '=COUNTIF(\'Feature Inventory\'!E:E,"Stub")'),
    ("Planned",     '=COUNTIF(\'Feature Inventory\'!E:E,"Planned")'),
    ("Not Started", '=COUNTIF(\'Feature Inventory\'!E:E,"Not Started")'),
]
ws["A11"] = "Status"
ws["B11"] = "Count"
style_header_row(ws, 11, 2)
for i, (label, formula) in enumerate(counts, start=12):
    ws.cell(row=i, column=1, value=label).fill = STATUS_FILLS[label]
    ws.cell(row=i, column=1).border = BORDER
    ws.cell(row=i, column=2, value=formula).border = BORDER

ws["A19"] = "How to use this workbook"
ws["A19"].font = Font(bold=True, size=12)
howto = [
    "1. Feature Inventory: every feature/endpoint with current Status. Edit Status to 'Done'/'In Progress'/etc. and the Overview counts update.",
    "2. Roadmap: phased plan (Phase 2 build → Phase 3 migration → Phase 4 hardening → Phase 5 product growth). Update Target Date and Status as you go.",
    "3. Backlog: concrete TODOs/stubs identified in code right now. Pick from here when you sit down for a session.",
    "4. Tech Debt: known smells worth cleaning when convenient — not blocking.",
    "5. Sessions Log: append a row each time you work. Empty by default — use it as a 'where did I leave off' journal.",
    "Tip: when you start a session, sort Feature Inventory by Status to see what's still 'In Progress' or 'Stub'.",
]
for i, line in enumerate(howto, start=20):
    ws.cell(row=i, column=1, value=line).alignment = Alignment(wrap_text=True)
    ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=6)

autosize(ws, [22, 30, 30, 30, 30, 30])
ws.row_dimensions[2].height = 24

# =============================================================================
# Sheet 2: Feature Inventory
# =============================================================================
ws = wb.create_sheet("Feature Inventory")

inv_headers = ["Area", "Sub-area", "Feature", "Where it lives", "Status", "Evidence / TODO", "Notes"]

# (Area, Sub-area, Feature, Path, Status, Evidence, Notes)
inventory = [
    # ---- Backend: auth-service ---------------------------------------------
    ("Backend", "auth-service", "POST /auth/register — user registration", "services/auth-service/app/api/routes.py", "Done", "Real bcrypt hashing + uniqueness check", ""),
    ("Backend", "auth-service", "POST /auth/login — JWT issuance", "services/auth-service/app/api/routes.py", "Done", "", ""),
    ("Backend", "auth-service", "POST /auth/refresh — refresh token", "services/auth-service/app/api/routes.py", "Done", "", ""),
    ("Backend", "auth-service", "POST /auth/logout + /logout-all", "services/auth-service/app/api/routes.py", "Done", "", ""),
    ("Backend", "auth-service", "POST /auth/verify — token validation", "services/auth-service/app/api/routes.py", "Done", "", ""),
    ("Backend", "auth-service", "GET /auth/me — current user", "services/auth-service/app/api/routes.py", "Done", "", ""),
    ("Backend", "auth-service", "POST /auth/change-password", "services/auth-service/app/api/routes.py", "Done", "Logs out all sessions on change", ""),
    ("Backend", "auth-service", "POST /auth/reset-password — request", "services/auth-service/app/api/routes.py", "Partial", "Email delivery not wired", "Generates reset token but doesn't send email"),

    # ---- Backend: stock-data-service ---------------------------------------
    ("Backend", "stock-data-service", "Companies list / search / by group", "services/stock-data-service", "Done", "Live VNStock + DB cache", ""),
    ("Backend", "stock-data-service", "Stock detail + historical OHLCV", "services/stock-data-service", "Done", "", ""),
    ("Backend", "stock-data-service", "Company profile / news / events / dividends", "services/stock-data-service", "Done", "", ""),
    ("Backend", "stock-data-service", "Financials (income / balance / cashflow / ratios)", "services/stock-data-service", "Done", "Multi-period cached", ""),
    ("Backend", "stock-data-service", "Top gainers / losers / actives", "services/stock-data-service", "Done", "", ""),
    ("Backend", "stock-data-service", "Industries + companies by industry", "services/stock-data-service", "Done", "", ""),
    ("Backend", "stock-data-service", "Market indices (VNINDEX/VN30/HNX)", "services/stock-data-service", "Done", "", ""),
    ("Backend", "stock-data-service", "Priceboard + refresh", "services/stock-data-service", "Done", "Vietcap cache", ""),
    ("Backend", "stock-data-service", "ensure-and-sync (5y idempotent backfill)", "services/stock-data-service", "Done", "Called by portfolio on add", ""),

    # ---- Backend: portfolio-service ----------------------------------------
    ("Backend", "portfolio-service", "Portfolio CRUD", "services/portfolio-service", "Done", "", ""),
    ("Backend", "portfolio-service", "Holdings CRUD + price refresh", "services/portfolio-service", "Done", "", ""),
    ("Backend", "portfolio-service", "Transactions (single + bulk)", "services/portfolio-service", "Done", "", ""),
    ("Backend", "portfolio-service", "Price alerts CRUD", "services/portfolio-service", "Done", "", ""),
    ("Backend", "portfolio-service", "Watchlist add/remove/list", "services/portfolio-service", "Done", "", ""),
    ("Backend", "portfolio-service", "Default-portfolio convenience routes", "services/portfolio-service", "Done", "/holdings, /summary, /performance, /metrics", ""),
    ("Backend", "portfolio-service", "Alert evaluation on price events", "services/portfolio-service", "Planned", "Phase 2 plan: consume stock.price_updated", "Event-driven alerting not yet wired"),
    ("Backend", "portfolio-service", "Recommendations / prospective stocks", "services/portfolio-service", "Planned", "Listed in Phase 2 plan", "Frontend has mock fallbacks today"),

    # ---- Backend: prediction-service ---------------------------------------
    ("Backend", "prediction-service", "POST /predict + GET /predict/{symbol} + bulk", "services/prediction-service", "Done", "", ""),
    ("Backend", "prediction-service", "Models CRUD + training + features", "services/prediction-service", "Done", "13 model types seeded", ""),
    ("Backend", "prediction-service", "Backtesting + model comparison", "services/prediction-service", "Done", "", ""),
    ("Backend", "prediction-service", "Technical-indicator catalogue (CRUD)", "services/prediction-service", "Done", "60+ indicators seeded", ""),
    ("Backend", "prediction-service", "Solutions CRUD + train + predict", "services/prediction-service", "Done", "tbl_solution + training_result/prediction_result", ""),
    ("Backend", "prediction-service", "GET /simulation/trained-solutions", "services/prediction-service/app/api/routes.py:368", "Stub", "TODO: Implement trained solutions storage", "Returns empty array"),
    ("Backend", "prediction-service", "Time series CRUD", "services/prediction-service", "Partial", "Frontend service exists; backend coverage uneven", "Verify routes vs frontend timeSeriesService.js"),

    # ---- Backend: analysis-service -----------------------------------------
    ("Backend", "analysis-service", "Technical analysis /technical/{symbol}", "services/analysis-service", "Done", "RSI/MACD/SMA/support-resistance", ""),
    ("Backend", "analysis-service", "Fundamental analysis /fundamental/{symbol}", "services/analysis-service", "Done", "P/E, P/B, ROE, ROA, EPS", ""),
    ("Backend", "analysis-service", "Stock screener (POST + GET + saved configs)", "services/analysis-service", "Done", "", ""),
    ("Backend", "analysis-service", "Multi-stock comparison", "services/analysis-service", "Done", "", ""),
    ("Backend", "analysis-service", "Industry analysis /industry/{code}", "services/analysis-service", "Done", "", ""),
    ("Backend", "analysis-service", "Combined / summary / signals", "services/analysis-service", "Done", "", ""),

    # ---- Backend: ai-insights-service --------------------------------------
    ("Backend", "ai-insights-service", "Stock insight (POST/GET)", "services/ai-insights-service", "Done", "", ""),
    ("Backend", "ai-insights-service", "Stock comparison + news analysis + Q&A", "services/ai-insights-service", "Done", "", ""),
    ("Backend", "ai-insights-service", "Market overview + batch insights", "services/ai-insights-service", "Done", "", ""),
    ("Backend", "ai-insights-service", "Recommendations + portfolio insight", "services/ai-insights-service", "Done", "", ""),
    ("Backend", "ai-insights-service", "Comprehensive insights (AI score / risk / patterns)", "services/ai-insights-service", "Done", "", ""),
    ("Backend", "ai-insights-service", "GET /trending — trending topics & hot stocks", "services/ai-insights-service", "Partial", "Returns hardcoded mock (3 topics, 5 stocks)", "Wire to real news/social signal source"),
    ("Backend", "ai-insights-service", "GET /sectors — sector AI insights", "services/ai-insights-service", "Partial", "5 sectors hardcoded", "Wire to real data"),
    ("Backend", "ai-insights-service", "Real LLM integration (OpenAI/Anthropic)", "services/ai-insights-service", "Planned", "OPENAI/ANTHROPIC keys plumbed but not used", "InsightsService is in-house heuristic today"),

    # ---- Backend: chatbot-service ------------------------------------------
    ("Backend", "chatbot-service", "POST /chat + WS /ws/{session_id}", "services/chatbot-service", "Done", "Intent routing + session storage", ""),
    ("Backend", "chatbot-service", "History GET / DELETE / export", "services/chatbot-service", "Done", "JSON / TEXT / MARKDOWN", ""),
    ("Backend", "chatbot-service", "Suggestions / intents / feedback", "services/chatbot-service", "Done", "Hardcoded suggestion list (acceptable for v1)", ""),
    ("Backend", "chatbot-service", "GET /stats (admin)", "services/chatbot-service", "Partial", "Returns hardcoded mock stats", "Wire to real usage metrics"),

    # ---- Backend: journal-service ------------------------------------------
    ("Backend", "journal-service", "Account CRUD + trading rules CRUD", "services/journal-service", "Done", "", ""),
    ("Backend", "journal-service", "Trades CRUD + close + stop revision", "services/journal-service", "Done", "Schwager: stop only tightens", ""),
    ("Backend", "journal-service", "Trade diary + chart upload (PNG/JPEG/WebP/GIF)", "services/journal-service", "Done", "MAX_UPLOAD_SIZE_MB=10", ""),
    ("Backend", "journal-service", "Daily plans + weekly reviews", "services/journal-service", "Done", "Auto-computed weekly stats", ""),
    ("Backend", "journal-service", "Dashboard + equity snapshots", "services/journal-service", "Done", "", ""),
    ("Backend", "journal-service", "Unit / integration tests", "services/journal-service/tests", "Not Started", "0 test files", "Risk: changes can regress silently"),

    # ---- Backend: knowledge-qa-service -------------------------------------
    ("Backend", "knowledge-qa-service", "POST /chat (SSE streaming)", "services/knowledge-qa-service", "Done", "Graph RAG", ""),
    ("Backend", "knowledge-qa-service", "Search / history / clear / stats", "services/knowledge-qa-service", "Done", "", ""),
    ("Backend", "knowledge-qa-service", "Neo4j + Ollama integration", "services/knowledge-qa-service", "Done", "Clean DDD layering", "Ollama profile gpu/cpu in docker-compose"),

    # ---- Backend: shared / infra -------------------------------------------
    ("Backend", "stock-common", "JWT auth lib + middleware", "stock-common/stock_common/auth", "Done", "", ""),
    ("Backend", "stock-common", "Async DB connection + repository base", "stock-common/stock_common/database", "Done", "", ""),
    ("Backend", "stock-common", "EventBus (aio-pika) + handlers", "stock-common/stock_common/events", "Done", "Library ready", "Few services actually publish/consume yet"),
    ("Backend", "stock-common", "Observability (structlog, Prometheus, OTLP)", "stock-common/stock_common/observability", "Done", "", ""),
    ("Backend", "stock-common", "Resilience (circuit breaker, retry)", "stock-common/stock_common/resilience", "Done", "", ""),
    ("Infra",   "Traefik gateway", "Path-based routing labels", "stock_microservices/docker-compose.yml", "Done", "", ""),
    ("Infra",   "RabbitMQ", "Container + definitions.json", "stock_microservices/rabbitmq", "Done", "", ""),
    ("Infra",   "Redis", "Cache + sessions", "stock_microservices/docker-compose.yml", "Done", "", ""),
    ("Infra",   "MySQL via SSH tunnel", "Remote DB tunnel container", "stock_microservices/docker-compose.yml", "Done", "Profile: remote-db", ""),
    ("Infra",   "Prometheus + Grafana + Jaeger", "Monitoring stack", "stock_microservices/monitoring", "Done", "", ""),
    ("Infra",   "Ollama (gpu/cpu profiles)", "Local LLM server", "stock_microservices/docker-compose.yml", "Done", "", ""),

    # ---- Migration / cutover -----------------------------------------------
    ("Migration", "scripts", "001 users / 002 companies / 003 portfolios / 004 transactions", "stock_microservices/migrations/scripts", "Done", "Scripts present", ""),
    ("Migration", "scripts", "005 alerts / 006 models / 007 predictions", "stock_microservices/migrations/scripts", "Planned", "Listed in Phase 3 plan, not present", ""),
    ("Migration", "verify", "verify_migration.py", "stock_microservices/migrations/verify", "Partial", "Folder present; coverage TBD", "Audit completeness"),
    ("Migration", "sync", "Continuous Django→microservice sync", "stock_microservices/migrations/sync", "Partial", "Skeleton present", "Per-table sync coverage TBD"),
    ("Migration", "rollback", "Emergency rollback scripts", "stock_microservices/migrations/rollback", "Partial", "Folder present", "Validate against current schemas"),
    ("Migration", "shadow mode", "Shadow comparator service + Traefik mirroring", "(not implemented)", "Planned", "Phase 3.2", ""),
    ("Migration", "cutover", "Feature flags + weighted Traefik routing", "stock_microservices/feature-flags, cutover/", "Partial", "Folders + cutover.py exist", "Validate end-to-end runbook"),
    ("Migration", "decommission", "Django decommission", "(not implemented)", "Planned", "Phase 3.6", "Gate on 100% traffic + 2 weeks soak"),

    # ---- Frontend: routing & layout ----------------------------------------
    ("Frontend", "Layout", "MainLayout + Sidebar + Header", "src/components/Layout", "Done", "", ""),
    ("Frontend", "Routing", "Custom RouterContext (string-based)", "src/context", "Tech Debt", "react-router-dom installed but unused", "Migrate to <Routes> for browser back/forward + URLs"),
    ("Frontend", "Routes", "screener / calculator / watchlist", "src/components/Layout/MainLayout.js:131-135", "Stub", "All map to Dashboard", "Implement or remove from sidebar"),

    # ---- Frontend: auth ----------------------------------------------------
    ("Frontend", "Auth", "Login / Register / Reset / Change password", "src/components/Auth/LoginForm.js", "Done", "", ""),
    ("Frontend", "Auth", "Token refresh on 401", "src/services/httpClient.js", "Partial", "401 logs out; no auto-refresh", "Implement refresh-token interceptor"),

    # ---- Frontend: dashboard / portfolio -----------------------------------
    ("Frontend", "Dashboard", "Dashboard widgets (metrics, recommendations, holdings)", "src/components/Dashboard", "Done", "", ""),
    ("Frontend", "Dashboard", "Real recommendations / prospective stocks", "src/services/api.js:691-793", "Partial", "Falls back to mocks (FPT, MWG, VHM…)", "Wire to AI service real data"),
    ("Frontend", "Portfolio", "Holdings / Performance / Alerts pages", "src/components/Pages", "Done", "", ""),

    # ---- Frontend: market data --------------------------------------------
    ("Frontend", "Market", "Priceboard (VN30 + refresh)", "src/components/Pages", "Done", "PriceBoardWrapper is thin", ""),
    ("Frontend", "Market", "Top gainers / losers / actives", "src/components/MarketMovers", "Done", "", ""),
    ("Frontend", "Market", "Stock screener / by-industry / stock list", "src/components/Pages/Stocks.js", "Done", "", ""),

    # ---- Frontend: company -------------------------------------------------
    ("Frontend", "Company", "Company tabs (overview/profile/charts/dividends/events)", "src/components/Pages/Company", "Done", "", ""),
    ("Frontend", "Company", "Financial reports (IS / BS / CF / Ratios)", "src/components/Pages/Company/Reports", "Done", "", ""),

    # ---- Frontend: prediction / ML ----------------------------------------
    ("Frontend", "Prediction", "Time series CRUD UI", "src/components/Pages/TimeSeries", "Done", "", ""),
    ("Frontend", "Prediction", "Models list + detail", "src/components/Pages/models", "Done", "", ""),
    ("Frontend", "Prediction", "Solutions list / new / edit (train + predict tabs)", "src/components/Pages/Solutions", "In Progress", "Training-status polling incomplete", "Wire isPolling to backend status endpoint"),
    ("Frontend", "Prediction", "Indicators library page", "src/components/Pages/Indicators", "Done", "", ""),
    ("Frontend", "Prediction", "Simulation dashboard", "src/components/Pages/SimulationDashboard.js", "Partial", "Empty state shown when no results", "Backend /simulation/trained-solutions is a stub"),

    # ---- Frontend: analysis / AI ------------------------------------------
    ("Frontend", "Analysis", "Technical analysis page (charts + indicators)", "src/components/Pages/TechnicalAnalysis.js", "Partial", "Line 727: TODO Apply indicators to chart", "Indicators not yet rendered on chart"),
    ("Frontend", "Analysis", "Fundamental analysis page", "src/components/Pages/FundamentalAnalysis.js", "Done", "", ""),
    ("Frontend", "AI",       "AI Insights page", "src/components/Pages/AIInsights.js", "Done", "", ""),
    ("Frontend", "AI",       "Agents page", "src/components/Pages/Agent.js", "Done", "", ""),
    ("Frontend", "AI",       "Chatbot UI", "src/components/Pages/ChatbotAgent.js", "Done", "", ""),
    ("Frontend", "AI",       "Knowledge QA chat (SSE streaming)", "src/components/Pages/KnowledgeQAChat.js", "Done", "Graph RAG", ""),

    # ---- Frontend: journal -------------------------------------------------
    ("Frontend", "Journal", "Accounts page", "src/components/Pages/Journal/JournalAccounts.js", "Done", "", ""),
    ("Frontend", "Journal", "Dashboard (equity curve, stats)", "src/components/Pages/Journal/JournalDashboard.js", "Done", "", ""),
    ("Frontend", "Journal", "Trade Log + Trade Diary", "src/components/Pages/Journal", "Done", "", ""),
    ("Frontend", "Journal", "Daily Planning + Weekly Review", "src/components/Pages/Journal", "Done", "", ""),

    # ---- Frontend: shared --------------------------------------------------
    ("Frontend", "Services", "Centralized API constants + httpClient", "src/services, src/constants/api.js", "Done", "", ""),
    ("Frontend", "Services", "Per-service modules (12 files)", "src/services", "Done", "company/portfolio/model/solution/timeSeries/indicator/journal/knowledgeQA/chatbotAgent/file", ""),
    ("Frontend", "UI",       "Reusable UI (LoadingSpinner, ErrorMessage, ConfirmDialog, DataTable)", "src/components/ui", "Done", "", ""),
]

write_rows(ws, inv_headers, inventory)
autosize(ws, [12, 20, 50, 38, 14, 38, 36])
ws.auto_filter.ref = f"A1:{get_column_letter(len(inv_headers))}{len(inventory)+1}"
add_status_conditional(ws, "E", 2, len(inventory) + 1)

# Data validation on Status column
from openpyxl.worksheet.datavalidation import DataValidation
dv = DataValidation(type="list", formula1='"Done,In Progress,Partial,Stub,Planned,Not Started,Blocked,Tech Debt"', allow_blank=True)
dv.add(f"E2:E{len(inventory)+1}")
ws.add_data_validation(dv)

# =============================================================================
# Sheet 3: Roadmap
# =============================================================================
ws = wb.create_sheet("Roadmap")

rm_headers = ["Phase", "Track", "Milestone", "Concrete tasks", "Priority", "Status", "Target", "Owner", "Notes"]

roadmap = [
    # ---- Phase 2: build (mostly done) --------------------------------------
    ("Phase 2 — Build microservices", "auth-service",         "User auth & JWT",                      "Register/login/refresh/logout/me/change/reset",                                  "P0", "Done",        "",            "you", "Email delivery on reset still TODO"),
    ("Phase 2 — Build microservices", "stock-data-service",   "Stock + market data",                  "Companies/stocks/financials/priceboard/indices",                                  "P0", "Done",        "",            "you", "VNStock-backed"),
    ("Phase 2 — Build microservices", "portfolio-service",    "Portfolio + alerts",                   "Portfolios, holdings, transactions, alerts, watchlist",                           "P0", "Done",        "",            "you", "Event-driven alerting still planned"),
    ("Phase 2 — Build microservices", "prediction-service",   "ML training + prediction",             "Models, solutions, training, prediction, backtest, indicators",                   "P1", "Done",        "",            "you", "Trained-solutions storage stub remains"),
    ("Phase 2 — Build microservices", "analysis-service",     "Technical + fundamental analysis",     "Technical, fundamental, screener, compare, signals, summary",                     "P1", "Done",        "",            "you", ""),
    ("Phase 2 — Build microservices", "ai-insights-service",  "AI insights",                          "Insight, compare, news, Q&A, market overview, comprehensive",                     "P1", "Done",        "",            "you", "Real LLM not yet integrated"),
    ("Phase 2 — Build microservices", "chatbot-service",      "Conversational chatbot",               "/chat, WS, history, export, intents",                                             "P2", "Done",        "",            "you", ""),
    ("Phase 2 — Build microservices", "journal-service",      "Trader journal (Schwager)",            "Accounts, rules, trades, diaries, plans, reviews, equity",                        "P1", "Done",        "",            "you", "Add tests"),
    ("Phase 2 — Build microservices", "knowledge-qa-service", "Graph RAG knowledge Q&A",              "Neo4j + Ollama + SSE chat + search",                                              "P1", "Done",        "",            "you", ""),

    # ---- Phase 3: migration (in flight) ------------------------------------
    ("Phase 3 — Migration",           "3.1 testing",          "Integration test suite",               "9 integration files passing; add e2e + performance + security",                  "P0", "In Progress", "",            "you", "180 pass, 25 skip last run"),
    ("Phase 3 — Migration",           "3.1 testing",          "Add journal-service tests",            "Unit + integration for accounts/trades/diary/plans/reviews",                      "P0", "Not Started", "",            "you", "Currently 0 tests"),
    ("Phase 3 — Migration",           "3.1 testing",          "Coverage ≥ 80%",                       "pytest --cov; raise gaps",                                                        "P1", "Not Started", "",            "you", ""),
    ("Phase 3 — Migration",           "3.2 shadow",           "Shadow comparator service",            "Build comparator + Traefik mirroring + diff log + Grafana panel",                 "P1", "Planned",     "",            "you", "Optional if Django already off"),
    ("Phase 3 — Migration",           "3.3 data",             "Migration scripts 005-007",            "alerts, ml_model, predictions migration scripts",                                 "P1", "Planned",     "",            "you", "Plan lists them; not present"),
    ("Phase 3 — Migration",           "3.3 data",             "verify_migration.py end-to-end",       "Counts + sample rows + checksum per table",                                       "P1", "Partial",     "",            "you", "Folder present"),
    ("Phase 3 — Migration",           "3.3 data",             "Continuous sync (shadow window)",      "RabbitMQ-driven Django → microservice sync",                                      "P1", "Partial",     "",            "you", "sync/ skeleton present"),
    ("Phase 3 — Migration",           "3.4 cutover",          "Feature flags + weighted routing",     "Roll 10% → 30% → 50% → 100% per service",                                         "P1", "Partial",     "",            "you", "feature-flags/ + cutover.py present"),
    ("Phase 3 — Migration",           "3.4 cutover",          "Rollback runbook validated",           "scripts/rollback.sh dry-run on staging",                                          "P1", "Planned",     "",            "you", ""),
    ("Phase 3 — Migration",           "3.5 hardening",        "Security audit checklist",             "JWT, RBAC, rate limit, TLS, secrets, mTLS, SAST",                                 "P0", "Not Started", "",            "you", ""),
    ("Phase 3 — Migration",           "3.5 hardening",        "Performance targets",                  "p99 < 300ms; throughput per Phase 3 doc",                                          "P1", "Not Started", "",            "you", ""),
    ("Phase 3 — Migration",           "3.5 hardening",        "HA + DR drill",                        "Replicas, anti-affinity, backups, DR runbook",                                    "P2", "Not Started", "",            "you", ""),
    ("Phase 3 — Migration",           "3.6 decommission",     "Django decommission",                  "Archive code, drop endpoints, clean compose",                                     "P2", "Planned",     "",            "you", "Gate on 2 weeks at 100%"),

    # ---- Phase 4: product polish (next) -----------------------------------
    ("Phase 4 — Polish & gaps",       "Backend",              "Wire reset-password email",            "SMTP + template + token expiration",                                              "P1", "Not Started", "",            "you", ""),
    ("Phase 4 — Polish & gaps",       "Backend",              "Replace mock /trending and /sectors",  "ai-insights-service: real signal source",                                         "P2", "Not Started", "",            "you", ""),
    ("Phase 4 — Polish & gaps",       "Backend",              "Implement /simulation/trained-solutions","Persist trained solutions; expose to UI",                                       "P1", "Not Started", "",            "you", "Currently returns []"),
    ("Phase 4 — Polish & gaps",       "Backend",              "Event-driven price alerts",            "Consume stock.price_updated → trigger alert.triggered",                           "P1", "Not Started", "",            "you", "stock-common EventBus already exists"),
    ("Phase 4 — Polish & gaps",       "Backend",              "Real LLM integration (insights/chat)",  "Plumb OPENAI_API_KEY/ANTHROPIC_API_KEY through InsightsService",                 "P1", "Not Started", "",            "you", "Keys plumbed but unused"),
    ("Phase 4 — Polish & gaps",       "Frontend",             "Render indicators on technical chart", "TechnicalAnalysis.js:727 TODO",                                                   "P1", "Not Started", "",            "you", ""),
    ("Phase 4 — Polish & gaps",       "Frontend",             "Auto refresh-token interceptor",       "On 401, retry once with refresh token",                                           "P1", "Not Started", "",            "you", ""),
    ("Phase 4 — Polish & gaps",       "Frontend",             "Implement screener / calculator / watchlist routes", "Real pages instead of Dashboard fallback",                          "P1", "Not Started", "",            "you", "MainLayout.js:131-135"),
    ("Phase 4 — Polish & gaps",       "Frontend",             "Solution training-status live polling", "Wire isPolling to backend solution status",                                      "P1", "Not Started", "",            "you", ""),
    ("Phase 4 — Polish & gaps",       "Frontend",             "Replace dashboard mock fallbacks",      "Remove hardcoded recommendations/prospective stocks",                             "P2", "Not Started", "",            "you", "api.js:691-793"),

    # ---- Phase 5: product growth ------------------------------------------
    ("Phase 5 — Growth",              "Product",              "Mobile-friendly responsive pass",      "Audit all pages on small screens",                                                "P2", "Not Started", "",            "you", ""),
    ("Phase 5 — Growth",              "Product",              "Notifications (push / email / web)",   "Triggered by alert/journal/training events",                                       "P2", "Not Started", "",            "you", ""),
    ("Phase 5 — Growth",              "Product",              "Backtesting UI",                       "Frontend wrapper for /backtest endpoint",                                         "P2", "Not Started", "",            "you", ""),
    ("Phase 5 — Growth",              "Product",              "Multi-language (vi / en) i18n",        "i18next or react-intl",                                                           "P3", "Not Started", "",            "you", "Suggestions and intents already in vi"),
    ("Phase 5 — Growth",              "Quality",              "Frontend test suite",                  "Vitest/RTL — start with Auth, Dashboard, Solutions",                              "P1", "Not Started", "",            "you", "Currently no tests"),
    ("Phase 5 — Growth",              "Quality",              "API contract tests (Pact / schemathesis)","Per-service contract tests in CI",                                              "P2", "Not Started", "",            "you", ""),
    ("Phase 5 — Growth",              "Ops",                  "CI pipeline (lint + test + build)",    "GitHub Actions per service + frontend",                                            "P0", "Not Started", "",            "you", "Pre-commit hooks at minimum"),
    ("Phase 5 — Growth",              "Ops",                  "Container image registry + tags",      "Push images on tag; pin in compose",                                              "P1", "Not Started", "",            "you", ""),
]

write_rows(ws, rm_headers, roadmap)
autosize(ws, [28, 24, 36, 60, 10, 14, 12, 10, 36])
ws.auto_filter.ref = f"A1:{get_column_letter(len(rm_headers))}{len(roadmap)+1}"
add_status_conditional(ws, "F", 2, len(roadmap) + 1)
dv = DataValidation(type="list", formula1='"Done,In Progress,Partial,Stub,Planned,Not Started,Blocked,Tech Debt"', allow_blank=True)
dv.add(f"F2:F{len(roadmap)+1}")
ws.add_data_validation(dv)
dv2 = DataValidation(type="list", formula1='"P0,P1,P2,P3"', allow_blank=True)
dv2.add(f"E2:E{len(roadmap)+1}")
ws.add_data_validation(dv2)

# =============================================================================
# Sheet 4: Backlog (concrete TODOs spotted in code)
# =============================================================================
ws = wb.create_sheet("Backlog")

bl_headers = ["#", "Type", "Where", "What", "Status", "Why it matters", "Effort"]
backlog = [
    (1,  "Stub",       "services/prediction-service/app/api/routes.py:368", "TODO: Implement trained solutions storage — /simulation/trained-solutions returns []", "Not Started", "Frontend simulation dashboard cannot show trained solutions", "M"),
    (2,  "Mock",       "services/ai-insights-service /trending",            "Hardcoded 3 topics + 5 hot stocks",                                                    "Not Started", "Trending widget shows fake data",                            "M"),
    (3,  "Mock",       "services/ai-insights-service /sectors",             "Hardcoded 5 sectors with mock sentiment",                                              "Not Started", "Sector view is fake",                                        "M"),
    (4,  "Mock",       "services/chatbot-service /stats",                   "Returns hardcoded usage stats",                                                        "Not Started", "Admin can't see real chatbot usage",                          "S"),
    (5,  "Missing",    "services/auth-service reset-password",              "Generates token but doesn't email",                                                    "Not Started", "Reset flow is broken end-to-end",                            "M"),
    (6,  "Tests",      "services/journal-service",                          "Zero tests for ~37 endpoints",                                                         "Not Started", "Regressions go unnoticed; high-risk feature",                "L"),
    (7,  "Frontend",   "src/components/Pages/TechnicalAnalysis.js:727",     "TODO: Apply indicators to chart",                                                      "Not Started", "Indicators selected but not rendered on chart",              "M"),
    (8,  "Frontend",   "src/components/Layout/MainLayout.js:131-135",       "screener / calculator / watchlist routes map to Dashboard",                            "Not Started", "Dead nav links — confusing UX",                              "M"),
    (9,  "Frontend",   "src/services/api.js:262-278",                       "Mock searchStock fallback (VIC, VNM, VCB…)",                                           "Not Started", "Search shows fake data when API fails",                      "S"),
    (10, "Frontend",   "src/services/api.js:691-793",                       "Mock recommendations + prospective stocks fallback",                                   "Not Started", "Dashboard shows hardcoded picks",                            "S"),
    (11, "Frontend",   "src/services/httpClient.js",                        "401 → logout (no auto-refresh)",                                                       "Not Started", "Users get kicked instead of seamless refresh",               "M"),
    (12, "Frontend",   "src/components/Pages/Solutions/*",                  "isPolling state — training-status live polling incomplete",                            "In Progress", "Training UI doesn't reflect backend progress",               "M"),
    (13, "Frontend",   "src/components/Pages/Predict/PriceBoardWrapper.js", "Thin (7-line) wrapper — no caching/state",                                              "Not Started", "Likely fine, but verify",                                    "S"),
    (14, "Tech Debt",  "src/components/chatbot/FileUploadManager.js + src/components/common/FileUploadManager.js", "Duplicated implementations",                              "Not Started", "Drift risk; fix breaks one but not the other",               "S"),
    (15, "Tech Debt",  "src/services + src/components/StockChart.js + src/components/ui/StockChart.js", "Duplicate StockChart files",                                              "Not Started", "Pick one home",                                              "S"),
    (16, "Tech Debt",  "src/ (190+ console.log)",                           "Verbose dev logging in prod bundle",                                                   "Not Started", "Strip with eslint rule or build flag",                       "S"),
    (17, "Tech Debt",  "src/context/RouterContext.js",                      "Custom string router, react-router-dom installed but unused",                          "Not Started", "No URL routing → no back/forward, no deep links",            "L"),
    (18, "Migration",  "stock_microservices/migrations/scripts",            "005_alerts, 006_models, 007_predictions scripts missing",                              "Not Started", "Phase 3.3 plan calls for them",                              "M"),
    (19, "Migration",  "(not implemented) shadow comparator",               "Phase 3.2 shadow service + Traefik mirroring",                                          "Not Started", "Skip if Django already retired; otherwise required",         "L"),
    (20, "Migration",  "stock_microservices/migrations/verify",             "verify_migration.py coverage TBD",                                                     "Not Started", "Cannot prove migration completeness without it",             "M"),
    (21, "Backend",    "stock-common EventBus",                             "Library exists; few services publish/consume",                                         "Not Started", "Stock price alerts aren't event-driven yet",                 "M"),
    (22, "Backend",    "ai-insights-service real LLM",                      "OPENAI_API_KEY/ANTHROPIC_API_KEY plumbed, never called",                                "Not Started", "Insights are heuristic, not LLM",                            "M"),
    (23, "Ops",        "(not present) CI pipeline",                         "No GitHub Actions / pre-commit",                                                       "Not Started", "Tests only run when you remember",                           "M"),
    (24, "Ops",        "production/security",                               "Folder exists; rate limiting + secret store TBD",                                      "Not Started", "Phase 3.5 hardening",                                        "L"),
]

write_rows(ws, bl_headers, backlog)
autosize(ws, [5, 12, 60, 60, 14, 38, 8])
ws.auto_filter.ref = f"A1:{get_column_letter(len(bl_headers))}{len(backlog)+1}"
add_status_conditional(ws, "E", 2, len(backlog) + 1)
dv = DataValidation(type="list", formula1='"Done,In Progress,Partial,Stub,Planned,Not Started,Blocked,Tech Debt"', allow_blank=True)
dv.add(f"E2:E{len(backlog)+1}")
ws.add_data_validation(dv)
dv = DataValidation(type="list", formula1='"S,M,L,XL"', allow_blank=True)
dv.add(f"G2:G{len(backlog)+1}")
ws.add_data_validation(dv)

# =============================================================================
# Sheet 5: Tech Debt
# =============================================================================
ws = wb.create_sheet("Tech Debt")

td_headers = ["Area", "Item", "Where", "Impact", "Suggested fix", "Status"]
techdebt = [
    ("Frontend routing", "Custom RouterContext (string keys) instead of react-router-dom", "src/context/RouterContext.js", "No URL deep links, no back/forward, brittle dynamic routes", "Switch to <BrowserRouter><Routes>; one route → one component file", "Not Started"),
    ("Frontend duplication", "Two FileUploadManager files", "src/components/chatbot, src/components/common", "Drift between copies", "Keep common/, delete chatbot/, update imports", "Not Started"),
    ("Frontend duplication", "Two StockChart files", "src/components, src/components/ui", "Same as above", "Pick ui/ as canonical", "Not Started"),
    ("Frontend duplication", "react-table + react-data-table-component both present", "package.json", "Two table libs ship to bundle", "Pick one (react-data-table-component is in use)", "Not Started"),
    ("Frontend logging", "190+ console.log statements", "src/", "Noisy console + ships in prod bundle", "Eslint no-console rule + structured logger", "Not Started"),
    ("Frontend mocks", "Mock fallbacks in api.js (search/recommendations/prospective)", "src/services/api.js", "Fake data leaks into UI when API fails", "Show empty state + retry instead", "Not Started"),
    ("Backend tests",   "journal-service has 0 tests", "services/journal-service/tests", "Risky for a service with 37 endpoints", "Add unit + integration; mirror other services", "Not Started"),
    ("Backend mocks",   "ai-insights /trending and /sectors hardcoded", "services/ai-insights-service", "UI shows fake market context", "Wire to real news/social signals or hide", "Not Started"),
    ("Backend",         "Real LLM unwired (keys plumbed but unused)", "services/ai-insights-service, chatbot-service", "Insights are heuristic only", "Add Anthropic/OpenAI client calls behind a flag", "Not Started"),
    ("Backend",         "EventBus underused", "stock-common/events vs services", "Coupling via httpx instead of events", "Publish stock.price_updated; consume in portfolio for alerts", "Not Started"),
    ("Schema",          "prediction-service double schema source (SQLAlchemy + inline SQL)", "services/prediction-service/app/main.py", "Drift: change one, forget the other", "Pick one source; if SQL is for legacy, document and freeze", "Not Started"),
    ("Ops",             "No CI", "(not present)", "Tests run by hand; quality regresses silently", "GitHub Actions: lint + pytest + npm test on PR", "Not Started"),
    ("Ops",             "Default secrets in .env.example", ".env.example, docker-compose.yml", "Easy to ship insecure defaults", "Generate JWT_SECRET on first run; fail fast if default", "Not Started"),
    ("Docs",            "Multiple status docs (WORK_IN_PROGRESS.md, FIXES_APPLIED.md, PREDICTION_UPDATE_SUMMARY.md, CHATBOT_IMPLEMENTATION_SUMMARY.md)", "repo root + microservices/", "Drift; new readers don't know what's current", "This Excel + CLAUDE.md become the source; archive old docs", "Not Started"),
]
write_rows(ws, td_headers, techdebt)
autosize(ws, [22, 60, 50, 38, 50, 14])
ws.auto_filter.ref = f"A1:{get_column_letter(len(td_headers))}{len(techdebt)+1}"
add_status_conditional(ws, "F", 2, len(techdebt) + 1)
dv = DataValidation(type="list", formula1='"Done,In Progress,Partial,Stub,Planned,Not Started,Blocked,Tech Debt"', allow_blank=True)
dv.add(f"F2:F{len(techdebt)+1}")
ws.add_data_validation(dv)

# =============================================================================
# Sheet 6: Sessions Log (you write here)
# =============================================================================
ws = wb.create_sheet("Sessions Log")

sl_headers = ["Date", "Session focus", "What I changed", "What I learned / decided", "Where I left off (next-up)", "Blockers"]
write_rows(ws, sl_headers, [
    ("2026-04-30", "Initial roadmap & inventory", "Generated this workbook", "Phase 2 ~complete; Phase 3 partial; biggest gaps: journal tests, real LLM, frontend routing", "Pick one P0 from Backlog and start", ""),
])
autosize(ws, [12, 28, 50, 50, 50, 30])
ws.row_dimensions[2].height = 36

# Add a tip row in row 4
ws.cell(row=4, column=1, value="Append one row per session. Keep 'Where I left off' actionable — paste the file:line you'll open next time.")
ws.cell(row=4, column=1).font = SUBTITLE_FONT
ws.merge_cells("A4:F4")

# =============================================================================
# Sheet 7: Architecture map (for orientation)
# =============================================================================
ws = wb.create_sheet("Architecture")

ws["A1"] = "Service map — path → service → port"
ws["A1"].font = TITLE_FONT
ws.merge_cells("A1:F1")

arch_headers = ["Path prefix (gateway)", "Service", "Internal port", "Database/Stores", "Key external deps", "Notes"]
arch = [
    ("/auth",                "auth-service",         8007, "MySQL (users)",                "—",                       "Issues JWTs shared with all services"),
    ("/companies, /stocks, /market, /industries, /priceboards", "stock-data-service", 8001, "MySQL + Redis cache", "vnstock3 (live)", "Source for prices/financials"),
    ("/portfolio (+ alerts, watchlist)", "portfolio-service", 8003, "MySQL", "stock-data-service",      "Calls ensure-and-sync on add"),
    ("/predictions, /predict, /models, /solutions", "prediction-service", 8002, "MySQL + model files", "—", "13 model types; technical indicators catalogue"),
    ("/analysis",            "analysis-service",     8004, "Reads stock-data-service",     "—",                       "Technical + fundamental + screener"),
    ("/ai",                  "ai-insights-service",  8005, "Stateless",                    "OpenAI/Anthropic (planned)","Heuristic insights today"),
    ("/chat",                "chatbot-service",      8006, "MySQL (sessions)",             "—",                       "Intent routing + WS"),
    ("/journal",             "journal-service",      8008, "MySQL + uploaded charts",      "—",                       "Schwager planned-trading model"),
    ("/knowledge-qa",        "knowledge-qa-service", 8009, "Neo4j (graph)",                "Ollama (local LLM)",      "SSE streaming chat"),
    ("Gateway",              "Traefik",              8004, "—",                            "—",                       "Routes by PathPrefix labels in compose"),
    ("Cache",                "Redis",                6379, "—",                            "—",                       "Shared cache + sessions"),
    ("Bus",                  "RabbitMQ",             5672, "—",                            "—",                       "vhost /stock"),
    ("Tracing",              "Jaeger",               16686,"—",                            "OTLP from all services",  ""),
    ("Metrics",              "Prometheus + Grafana", 9090, "—",                            "/metrics on each service","Dashboards in monitoring/grafana"),
]
write_rows(ws, arch_headers, arch, header_row=3)
autosize(ws, [40, 22, 14, 28, 28, 40])

# =============================================================================
# Save
# =============================================================================
wb.save(OUT)
print(f"Wrote {OUT}")
