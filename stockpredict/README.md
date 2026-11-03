# StockPredict

Vietnamese-stock-market platform: portfolio tracking, ML price prediction, technical/fundamental analysis, AI insights, an LLM chatbot, a Schwager-style trader journal, and a Graph-RAG knowledge Q&A.

Stack: 9 FastAPI microservices behind Traefik + React 19 + MySQL + Redis + RabbitMQ + Prometheus/Grafana/Jaeger + Neo4j + Ollama.

## Where am I? Open `ROADMAP.xlsx` first

`ROADMAP.xlsx` (in this directory) is the project's living plan and status board. Open it before starting any work — it tells you what's done, what's in flight, and what you said you'd do next.

Sheets:

| Sheet | Purpose |
|---|---|
| **Overview** | Snapshot + auto-counted status totals + how-to-use guide |
| **Feature Inventory** | Every feature/endpoint with current Status — filterable, color-coded |
| **Roadmap** | Phased plan (Phase 2 build → Phase 3 migration → Phase 4 polish → Phase 5 growth) |
| **Backlog** | Concrete TODOs spotted in code, with `file:line` references and effort sizing |
| **Tech Debt** | Smells worth cleaning when convenient |
| **Sessions Log** | One row per work session — read the last row's "Where I left off" |
| **Architecture** | Path → service → port → deps map |

### Working rhythm

1. Open `ROADMAP.xlsx` → **Sessions Log** → read the last row.
2. Pick one item from **Backlog** (or the next "In Progress" row in **Feature Inventory**).
3. Work. Test.
4. Update the **Status** column on the row you touched (dropdown: Done / In Progress / Partial / Stub / Planned / Not Started / Blocked / Tech Debt).
5. Append a row to **Sessions Log**. The "Where I left off" cell is the most important field — paste the exact `file:line` you'll open next time.

### Regenerating the workbook

For structural changes (new features, new sheets), edit `build_roadmap_excel.py` and run:

```bash
python3 build_roadmap_excel.py
```

For routine status updates, edit `ROADMAP.xlsx` directly — the script overwrites, so don't both at once.

## Running the stack

```bash
./deploy.sh           # bring up frontend + microservices + monitoring
./deploy.sh --status  # see what's running
./deploy.sh --logs <service>
./deploy.sh --stop
```

Frontend: <http://localhost:3004>
Gateway: <http://localhost:8004>
Grafana: <http://localhost:3100>

For development details (commands per service, test runners, conventions), see `CLAUDE.md`.

## Tài liệu người dùng / User documentation

| Tài liệu / Document | Nội dung / Covers |
|---|---|
| [`docs/QUICK_START_GUIDE.md`](docs/QUICK_START_GUIDE.md) | **Bắt đầu ở đây.** Hướng dẫn nhanh toàn bộ ứng dụng, song ngữ Việt/Anh, 12 nhóm menu. / **Start here.** Whole-application quick guide, bilingual, all twelve menu groups. |
| [`docs/USER_GUIDE_portfolio_journal_ai_insights.md`](docs/USER_GUIDE_portfolio_journal_ai_insights.md) | Chuyên sâu: danh mục, nhật ký giao dịch, phân tích AI. / Deep dive: portfolio, trade journal, AI insights. |
| [`docs/USER_GUIDE_chart_decomp_and_decision_tools.md`](docs/USER_GUIDE_chart_decomp_and_decision_tools.md) | Chuyên sâu: phân rã biểu đồ và Decision Helper. / Deep dive: chart decomposition and Decision Helper. |
| [`docs/ANNOUNCEMENT_COPY.md`](docs/ANNOUNCEMENT_COPY.md) | Nội dung giới thiệu sẵn dùng cho LinkedIn / Facebook. / Ready-to-post announcement copy. |

Góp ý trong ứng dụng: menu **Góp ý & ý tưởng**.
In-app feedback: the **Ideas & feedback** menu.
