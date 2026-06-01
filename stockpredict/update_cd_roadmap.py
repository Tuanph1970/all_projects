"""Update roadmap_version_2.xlsx to reflect CD-1 through CD-5 completion.

WARNING: this is a one-shot incremental mutator, not an idempotent rebuild.
It APPENDS a row to the Session Log every run, and it does NOT know about the
CD-6 / CD-7 rows (those live only in the workbook). Do not blindly re-run it —
edit the workbook directly for routine status updates.
"""
import openpyxl

WB_PATH = "roadmap_version_2.xlsx"

wb = openpyxl.load_workbook(WB_PATH)

# ── CD Tasks: update Status column (col G = index 7, 1-based) ──────────────
ws_tasks = wb["CD Tasks"]
done_phases = {"CD-1", "CD-2", "CD-3", "CD-4"}
done_task_ids = {
    f"CD-{phase_num}{seq:02d}"
    for phase_num in range(1, 6)
    for seq in range(1, 11)
}

for row in ws_tasks.iter_rows(min_row=5):
    task_id = row[0].value
    if task_id and str(task_id).startswith("CD-"):
        phase = row[1].value  # col B
        if task_id in done_task_ids and phase in done_phases:
            row[6].value = "Done"   # col G
        elif task_id.startswith("CD-5"):
            row[6].value = "Done"   # CD-501..506 all shipped (incl. test_e2e_heston.py)

# ── CD Overview: update Status column (col G = index 7) ───────────────────
ws_overview = wb["CD Overview"]
phase_status = {
    "CD-1": "Done",
    "CD-2": "Done",
    "CD-3": "Done",
    "CD-4": "Done",
    "CD-5": "Done",   # CD-506 test_e2e_heston.py now exists
}
for row in ws_overview.iter_rows(min_row=5):
    phase_id = row[0].value
    if phase_id in phase_status:
        row[6].value = phase_status[phase_id]

# Also update the subtitle row (row 2) to reflect completion
ws_overview["A2"] = (
    "SRS: SRS_master_chart_system.md  |  As of 2026-06-01  |  "
    "Status: CD-1..CD-7 Done (Part I + Part II + clean-ups all shipped)"
)

# ── Session Log: append new session row ────────────────────────────────────
ws_log = wb["Session Log"]
# Find next empty row after existing data
last_row = ws_log.max_row + 1

session_data = [
    "2026-05-27",
    "Chart Decomp (CD-2 / CD-3 / CD-4)",
    (
        "CD-2: chart-decomp-service FastAPI microservice\n"
        "  • Port 8011, Traefik PathPrefix /stock_helper/api/v2/chart-decomp\n"
        "  • 13 endpoints: POST /decompose/{modwt,emd,eemd,vmd}, "
        "/time-freq/{cwt,hht}, /hurst, /coherence,\n"
        "    /forecast/{har,vmd-har,compare}, /realized-vol, /backtest/vol-target\n"
        "  • Library smoke-test on startup; /health/ready returns 503 if it fails\n"
        "  • Dockerfile installs stock-common + chart-decomp-lib with -e\n"
        "  • docker-compose.yml entry + Traefik labels added\n"
        "CD-3: ChartDecomp frontend viewer (src/components/Pages/ChartDecomp/index.js)\n"
        "  • Route /chart-decomp — 4 tabs: Decomp, Time-Freq, Hurst, Forecast\n"
        "  • InputPanel: ticker picker + 512-pt AR(1)+harmonic demo generator\n"
        "  • ComponentChart: stacked recharts LineChart with optional COI markers\n"
        "  • ScalogramCanvas: HTML5 canvas Viridis heatmap with COI mask\n"
        "  • HurstTab: Ĥ estimate + regime label + log₂-variance chart\n"
        "  • ForecastTab: walk-forward HAR/VMD-HAR comparison + metric cards\n"
        "  • Bilingual vi/en i18n (~90 new keys per locale)\n"
        "CD-4: VolForecastPage (src/components/Pages/ChartDecomp/VolForecastPage.js)\n"
        "  • Route /vol-forecast — 3 panels: Data, Compare, Backtest\n"
        "  • ComparePanel: HAR vs VMD-HAR with DM-stat badge (green if >1.96),\n"
        "    winner banner (C4: ΔRMSE+ΔQLIKE+DM>1.96 all required), metric delta table\n"
        "  • BacktestPanel: vol-targeting equity curve + drawdown + positions + turnover\n"
        "  • pricesToLogRV / logRVToAnnVol utilities; 756-day demo path\n"
        "  • POST /forecast/compare backend endpoint (single round-trip for DM test)"
    ),
    (
        "stock_microservices/services/chart-decomp-service/ (new)\n"
        "stock_microservices/chart-decomp-lib/ (new)\n"
        "stock_microservices/docker-compose.yml\n"
        "src/components/Pages/ChartDecomp/index.js (new)\n"
        "src/components/Pages/ChartDecomp/VolForecastPage.js (new)\n"
        "src/services/chartDecompService.js (new)\n"
        "src/constants/api.js (+14 CHART_DECOMP_* endpoints)\n"
        "src/components/Layout/MainLayout.js (2 new routes)\n"
        "src/components/Layout/Sidebar.js (chart-decomp + vol-forecast submenu)\n"
        "src/i18n/locales/vi.json + en.json (+150 keys each)\n"
        "SRS_chart_decomposition.md (new)\n"
        "roadmap_version_2.xlsx"
    ),
    (
        "CD-1 through CD-4 fully implemented.\n"
        "CD-5: test files CD-501..505 exist (unit/statistical/causality);\n"
        "  CD-506 (test_e2e_heston.py) not yet written — marked Partial.\n"
        "Known fix applied in CD-2: facade kwargs (not params objects);\n"
        "  HurstResult.H / .variances fields; split refit_vmd_every/refit_model_every."
    ),
    (
        "CD-5 test_e2e_heston.py — 2500-day Heston SV path end-to-end test.\n"
        "Verify CD-3 and CD-4 pages in browser once backend is running.\n"
        "Consider npm run build to check for any remaining import/TS issues."
    ),
]

for col_idx, value in enumerate(session_data, start=1):
    ws_log.cell(row=last_row, column=col_idx, value=value)

wb.save(WB_PATH)
print(f"Saved {WB_PATH}")
print(f"  • CD Tasks: updated statuses (Done/Planned)")
print(f"  • CD Overview: CD-1–CD-5 Done (CD-6/CD-7 maintained directly in workbook)")
print(f"  • Session Log: appended row {last_row}")
