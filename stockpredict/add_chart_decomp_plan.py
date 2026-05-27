"""Add Chart Decomposition module plan sheets to roadmap_version_2.xlsx.

Run: python3 add_chart_decomp_plan.py
Appends three new sheets without touching existing ones.
"""
from __future__ import annotations
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

XLSX = "/home/tuanph/TuanPH/all_projects/stockpredict/roadmap_version_2.xlsx"

# ── Shared styles ──────────────────────────────────────────────────────────────
THIN   = Side(style="thin",   color="BFBFBF")
MEDIUM = Side(style="medium", color="9E9E9E")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BORDER_THICK_TOP = Border(left=THIN, right=THIN, top=MEDIUM, bottom=THIN)

HEADER_FILL   = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT   = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
TITLE_FONT    = Font(name="Calibri", bold=True, size=16, color="1F4E78")
SUBTITLE_FONT = Font(name="Calibri", italic=True, size=10, color="595959")
PHASE_TITLE_FONT = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
NORMAL_FONT   = Font(name="Calibri", size=10)
BOLD_FONT     = Font(name="Calibri", bold=True, size=10)
MONO_FONT     = Font(name="Courier New", size=9)

STATUS_FILLS = {
    "Done":         PatternFill("solid", fgColor="C6EFCE"),
    "In Progress":  PatternFill("solid", fgColor="FFEB9C"),
    "Planned":      PatternFill("solid", fgColor="DDEBF7"),
    "Not Started":  PatternFill("solid", fgColor="F2F2F2"),
    "Blocked":      PatternFill("solid", fgColor="FFC7CE"),
}

PHASE_FILLS = {
    "CD-1": PatternFill("solid", fgColor="1F4E78"),  # navy  — backend lib
    "CD-2": PatternFill("solid", fgColor="2E75B6"),  # blue  — FastAPI service
    "CD-3": PatternFill("solid", fgColor="375623"),  # green — frontend decomp
    "CD-4": PatternFill("solid", fgColor="7030A0"),  # purple— frontend forecast
    "CD-5": PatternFill("solid", fgColor="C55A11"),  # orange— testing
}

EFFORT_FILLS = {
    "S":  PatternFill("solid", fgColor="E2EFDA"),
    "M":  PatternFill("solid", fgColor="FFEB9C"),
    "L":  PatternFill("solid", fgColor="FCE4D6"),
    "XL": PatternFill("solid", fgColor="FFC7CE"),
}


def cell(ws, row, col_idx, value, font=None, fill=None, align=None, border=True):
    c = ws.cell(row=row, column=col_idx, value=value)
    c.font      = font  or NORMAL_FONT
    c.alignment = align or Alignment(vertical="top", wrap_text=True)
    if fill:   c.fill   = fill
    if border: c.border = BORDER
    return c


def header_row(ws, row, headers, fill=None):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.fill      = fill or HEADER_FILL
        c.font      = HEADER_FONT
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border    = BORDER


def autosize(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def title_block(ws, text, subtitle, span_cols):
    ws.merge_cells(f"A1:{get_column_letter(span_cols)}1")
    c = ws["A1"]
    c.value     = text
    c.font      = TITLE_FONT
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    ws.merge_cells(f"A2:{get_column_letter(span_cols)}2")
    c = ws["A2"]
    c.value     = subtitle
    c.font      = SUBTITLE_FONT
    c.alignment = Alignment(horizontal="center", vertical="center")


# ══════════════════════════════════════════════════════════════════════════════
#  Sheet: "CD Overview"
# ══════════════════════════════════════════════════════════════════════════════
def build_cd_overview(wb):
    ws = wb.create_sheet("CD Overview")
    ws.sheet_view.showGridLines = False

    title_block(
        ws,
        "Chart Decomposition Module — Phase Plan",
        "SRS: SRS_chart_decomposition.md  |  As of 2026-05-27  |  Status: Planned",
        8,
    )

    headers = ["Phase", "Name", "Key Deliverables", "Primary Files / Libs",
               "Effort", "Duration Est.", "Status", "Notes"]
    header_row(ws, 4, headers)

    phases = [
        (
            "CD-1",
            "Backend Library\n(Python)",
            "• MODWTResult, EMDResult, VMDResult, TimeFreqResult, CoherenceResult dataclasses\n"
            "• modwt(), emd(), eemd(), vmd() decomposition functions\n"
            "• cwt_scalogram(), hilbert_spectrum() time-frequency views\n"
            "• hurst_wavelet() long-memory estimator\n"
            "• wavelet_coherence() bivariate analysis\n"
            "• realized_variance() / realized_vol() RV computation\n"
            "• Hybrid pipelines A (wavelet-denoise→EMD), B (EMD→CWT), C (MODWT→Hilbert)\n"
            "• NFR: < 100 ms MODWT, < 2 s VMD on len-1024",
            "chart_decomp/\n  decomp.py\n  time_freq.py\n  hurst.py\n  coherence.py\n  realized_vol.py\n  pipelines.py\n  types.py\n\nLibs: PyWavelets, PyEMD,\nvmdpy, SciPy, NumPy",
            "XL",
            "6–8 days",
            "Planned",
            "Pure-Python library with no web layer. Must satisfy causality constraint C1 "
            "(no look-ahead). All stochastic functions accept seed=. "
            "NFR-R1: input validation before algorithm. "
            "See Appendix B for implementation traps.",
        ),
        (
            "CD-2",
            "FastAPI Microservice\n(chart-decomp-service)",
            "• FastAPI app skeleton: /health/live, /health/ready, /metrics\n"
            "• POST /decompose/{modwt,emd,eemd,vmd,cwt,hht}\n"
            "• POST /hurst, POST /coherence\n"
            "• POST /forecast/{har,vmd-har}\n"
            "• POST /backtest/vol-target\n"
            "• CLI: chart-decompose decompose|hurst|forecast|backtest\n"
            "• Traefik label + compose entry on port 8011\n"
            "• Docker image + requirements",
            "stock_microservices/services/\n  chart-decomp-service/\n    app/\n      main.py\n      config.py\n      api/routes.py\n      services/\n    Dockerfile\n    requirements.txt\nchart_decomp/ (lib, installed -e)\ndocker-compose.yml (add service)",
            "L",
            "2–3 days",
            "Planned",
            "Thin HTTP wrapper around the chart_decomp library. "
            "Endpoints accept JSON arrays (user supplies data — per SRS §1.2). "
            "Large responses (scalogram arrays) should use streaming or numpy npz. "
            "Register /chart-decomp path prefix in Traefik.",
        ),
        (
            "CD-3",
            "Frontend — Decomposition\nViewer",
            "• Route: /chart-decomposition\n"
            "• SeriesInputPanel: stock symbol picker OR CSV upload\n"
            "• MODWTBandChart: stacked line charts (approx + D1–DJ)\n"
            "• CWTScalogram: heatmap, log-period y-axis, COI dashed overlay\n"
            "• HilbertSpectrum: Hilbert spectrum heatmap\n"
            "• HurstDiagnostics: log-log variance plot + Ĥ readout\n"
            "• WaveletCoherence: R² heatmap with phase arrows\n"
            "• Sidebar nav entry + en/vi i18n keys",
            "stock_react_javascript/stock-react-app/src/\n  pages/ChartDecomposition/\n    index.js\n    SeriesInputPanel.js\n    MODWTBandChart.js\n    CWTScalogram.js\n    HilbertSpectrum.js\n    HurstDiagnostics.js\n    CoherenceHeatmap.js\n  services/chartDecompService.js\n  constants/api.js (add endpoints)",
            "XL",
            "5–7 days",
            "Planned",
            "Heatmaps via recharts or d3. "
            "COI overlay must be rendered on all time-freq plots (NFR constraint B7). "
            "Phase arrows on coherence plot only where R² > 0.6 and outside COI. "
            "All API calls go through chartDecompService.js (no direct axios in components).",
        ),
        (
            "CD-4",
            "Frontend — Forecasting\n& Backtest UI",
            "• ForecastPanel: HAR vs VMD-HAR line chart overlaid with actuals\n"
            "• MetricsTable: RMSE, MAE, R², QLIKE, DM-stat side-by-side\n"
            "• BacktestEquityCurve: net PnL vs buy-and-hold vs naive vol-target\n"
            "• RollingVolChart: 30-day rolling strategy vol vs target line\n"
            "• PositionChart: position size over time\n"
            "• StrategyMetricsCard: Sharpe, MaxDD, turnover, cost drag",
            "stock_react_javascript/stock-react-app/src/\n  pages/ChartDecomposition/\n    ForecastPanel.js\n    MetricsTable.js\n    BacktestEquityCurve.js\n    RollingVolChart.js\n    StrategyMetricsCard.js",
            "L",
            "3–4 days",
            "Planned",
            "Forecast chart must label model as 'improves on HAR' only when all three "
            "conditions pass (ΔRMSE > 0, ΔQLIKE > 0, |DM| > 1.96) — per SRS §3.7.3. "
            "Backtest starts after minimum training window (no equity curve in burn-in).",
        ),
        (
            "CD-5",
            "Testing & Validation",
            "• Unit: round-trip reconstruction (MODWT 1e-10, EMD 1e-6, VMD 0.2 rel)\n"
            "• Unit: MODWT translation invariance\n"
            "• Unit: VMD mode count + ascending center-freq sort\n"
            "• Unit: edge robustness (N=100, 257, 1024, 5000)\n"
            "• Statistical: Hurst on fGn H∈{0.3,0.5,0.7,0.85}, N=4096, err≤0.07\n"
            "• Statistical: wavelet coherence validation (known-construction pair)\n"
            "• Causality: no-leakage swap test\n"
            "• Causality: deliberate look-ahead detector\n"
            "• E2E: 2500-day Heston SV path, HAR R²≥0.85 OOS,\n"
            "  rolling-vol within ±30% target on ≥70% days",
            "stock_microservices/services/chart-decomp-service/\n  tests/\n    test_decomp.py\n    test_time_freq.py\n    test_hurst.py\n    test_coherence.py\n    test_forecast.py\n    test_causality.py\n    test_e2e_heston.py",
            "L",
            "2–3 days",
            "Planned",
            "All stochastic tests use fixed seeds for reproducibility (NFR-RP1). "
            "E2E Heston test is marked @pytest.mark.slow and excluded from quick-test.sh. "
            "The look-ahead regression test must run in CI to guard against accidental leakage.",
        ),
    ]

    for r, (phase_id, name, deliverables, files, effort, duration, status, notes) in \
            enumerate(phases, start=5):
        fill = PHASE_FILLS.get(phase_id)
        cell(ws, r, 1, phase_id, font=PHASE_TITLE_FONT, fill=fill,
             align=Alignment(horizontal="center", vertical="center"))
        cell(ws, r, 2, name, font=Font(name="Calibri", bold=True, size=11))
        cell(ws, r, 3, deliverables)
        cell(ws, r, 4, files, font=MONO_FONT)
        cell(ws, r, 5, effort, font=BOLD_FONT, fill=EFFORT_FILLS.get(effort),
             align=Alignment(horizontal="center", vertical="center"))
        cell(ws, r, 6, duration, align=Alignment(horizontal="center", vertical="center"))
        cell(ws, r, 7, status, fill=STATUS_FILLS.get(status),
             align=Alignment(horizontal="center", vertical="center"))
        cell(ws, r, 8, notes)
        ws.row_dimensions[r].height = 110

    autosize(ws, [10, 20, 62, 38, 8, 12, 13, 52])
    ws.freeze_panes = "A5"

    # Total estimate row
    total_r = len(phases) + 5
    ws.merge_cells(f"A{total_r}:D{total_r}")
    c = ws.cell(row=total_r, column=1, value="Total estimate (new module end-to-end)")
    c.font      = BOLD_FONT
    c.border    = BORDER
    c.alignment = Alignment(horizontal="right", vertical="center")
    cell(ws, total_r, 5, "", border=True)
    cell(ws, total_r, 6, "18–25 days",
         font=Font(name="Calibri", bold=True, size=11, color="C55A11"),
         align=Alignment(horizontal="center", vertical="center"))
    cell(ws, total_r, 7, "Planned", fill=STATUS_FILLS["Planned"],
         align=Alignment(horizontal="center", vertical="center"))
    cell(ws, total_r, 8, "Assumes one developer. CD-1 and CD-3 can partially overlap once "
         "decomposition API shapes are agreed. CD-5 runs in parallel with CD-4.")
    ws.row_dimensions[total_r].height = 36

    # Effort legend
    leg = total_r + 2
    ws.cell(row=leg, column=1, value="Effort key:").font = Font(name="Calibri", bold=True, size=9)
    for i, (k, label) in enumerate([("S","<2 h"),("M","2–4 h"),("L","4–8 h"),("XL",">8 h")], 2):
        c = ws.cell(row=leg, column=i, value=f"{k} = {label}")
        c.fill      = EFFORT_FILLS[k]
        c.font      = Font(name="Calibri", size=9)
        c.border    = BORDER
        c.alignment = Alignment(horizontal="center")


# ══════════════════════════════════════════════════════════════════════════════
#  Sheet: "CD Tasks"
# ══════════════════════════════════════════════════════════════════════════════
def build_cd_tasks(wb):
    ws = wb.create_sheet("CD Tasks")
    ws.sheet_view.showGridLines = False

    title_block(ws, "Chart Decomposition — Detailed Task List",
                "Ref: SRS_chart_decomposition.md  |  2026-05-27", 9)

    headers = ["ID", "Phase", "Task", "Component / File",
               "Key API / Symbol", "Effort", "Status", "Depends On", "Notes / Pitfalls"]
    header_row(ws, 4, headers)

    tasks = [
        # ── Phase CD-1: Backend Library ────────────────────────────────────────
        ("CD-101", "CD-1", "Data-class result types",
         "chart_decomp/types.py",
         "MODWTResult, EMDResult, VMDResult,\nTimeFreqResult, CoherenceResult,\nForecastResult, BacktestResult",
         "S", "Planned", "",
         "Define all @dataclass types from SRS §4.1 first — they are the contract "
         "between backend modules and the API layer."),

        ("CD-102", "CD-1", "MODWT decomposition (FR-DECOMP-MODWT)",
         "chart_decomp/decomp.py\n→ modwt()",
         "pywt.swt(norm=True), sym8,\npad to next power-of-2,\nCOI width = (2^j-1)*(L-1)",
         "M", "Planned", "CD-101",
         "Pad to 2^n, run SWT, trim back. Symmetric boundary default. "
         "Return [A_J, D_J, …, D_1] — all length N. Must satisfy round-trip to 1e-10."),

        ("CD-103", "CD-1", "EMD & EEMD decomposition (FR-DECOMP-EMD)",
         "chart_decomp/decomp.py\n→ emd(), eemd()",
         "PyEMD.EMD, PyEMD.EEMD,\nn_trials=100, noise_width=0.2*std(x),\nperiod = 2*N/n_zero_crossings",
         "M", "Planned", "CD-101",
         "Sort IMFs highest→lowest freq (period ascending). Report dominant_periods. "
         "EEMD uses seed for noise perturbation (NFR-RP1). "
         "Trap B3: end effects — do not use final edge values in forecasting."),

        ("CD-104", "CD-1", "VMD decomposition (FR-DECOMP-VMD)",
         "chart_decomp/decomp.py\n→ vmd()",
         "vmdpy.VMD, K=5, alpha=1500,\nsort by center_freq ascending,\nsubtract/restore mean",
         "M", "Planned", "CD-101",
         "Sort modes by center frequency at every call (Trap B2). "
         "Report relative L2 reconstruction error. "
         "Trap B4: VMD is not exact reconstruction — do not interpret variance shares as 100%."),

        ("CD-105", "CD-1", "CWT scalogram (FR-TF-CWT)",
         "chart_decomp/time_freq.py\n→ cwt_scalogram()",
         "pywt.cwt, cmor1.5-1.0,\nscales=geomspace(2,256,64),\nCOI boundary array",
         "M", "Planned", "CD-101",
         "Return |W|², phase angle(W), COI as 1-D array indexed by time. "
         "COI = sqrt(2)*scale in samples for Morlet. "
         "Trap B7: COI must always be returned; plotting function must overlay it."),

        ("CD-106", "CD-1", "Hilbert spectrum / HHT (FR-TF-HHT)",
         "chart_decomp/time_freq.py\n→ hilbert_spectrum()",
         "scipy.signal.hilbert,\ninstantaneous freq via phase unwrapping,\nGaussian smoothing sigma=(1.5,4)",
         "M", "Planned", "CD-101",
         "Works on both EMD IMFs and MODWT detail bands. "
         "Accumulate A(t)² at bin f(t) per (component, time). "
         "Configurable Gaussian smoothing before return."),

        ("CD-107", "CD-1", "Hurst exponent via wavelet variance (FR-HURST)",
         "chart_decomp/hurst.py\n→ hurst_wavelet()",
         "MODWT Var(d_j) per level,\nregress log2_var on j,\nH = (slope+2)/2",
         "M", "Planned", "CD-102",
         "j_range=(2,8) by default — drops finest and coarsest scales. "
         "Return Ĥ, slope, intercept, full variance array, scale mask. "
         "Must pass statistical test: error ≤ 0.07 on fGn H∈{0.3,0.5,0.7,0.85}."),

        ("CD-108", "CD-1", "Wavelet coherence (FR-COH)",
         "chart_decomp/coherence.py\n→ wavelet_coherence()",
         "CWT W_x, W_y, cross-wavelet W_xy,\nsmooth in time (Gaussian σ∝scale),\nR²=|S(W_xy)|²/(S(|Wx|²)·S(|Wy|²))",
         "M", "Planned", "CD-105",
         "R² bounded [0,1]. Return phase array angle(S(W_xy)). "
         "Plot helper: phase arrows only where R²>0.6 and outside COI. "
         "Arrows: right=in-phase, left=anti, up=y-leads, down=x-leads."),

        ("CD-109", "CD-1", "Realized variance / vol (FR-RV)",
         "chart_decomp/realized_vol.py\n→ realized_variance(), realized_vol()",
         "RV=sum(r_intraday²),\nlog_rv=log(RV+eps),\nannualization=252",
         "S", "Planned", "CD-101",
         "Accept 2-D (days×intraday) or 1-D daily returns. "
         "Warn when 1-D is passed (r² is high-noise estimator). "
         "Return RV, vol, log_rv arrays."),

        ("CD-110", "CD-1", "Hybrid pipelines A, B, C (FR-HYB-*)",
         "chart_decomp/pipelines.py\n→ hybrid_a(), hybrid_b(), hybrid_c()",
         "Hybrid A: wavelet-denoise→EMD\nHybrid B: EMD→CWT-per-IMF\nHybrid C: MODWT→Hilbert",
         "M", "Planned", "CD-102,CD-103,CD-105,CD-106",
         "Hybrid A: zero finest k_drop=2 detail bands before EMD. "
         "Hybrid B: one CWT per IMF — detect residual mode mixing. "
         "Hybrid C: production-friendly (no mode mixing, fully reproducible)."),

        # ── Phase CD-2: FastAPI service ────────────────────────────────────────
        ("CD-201", "CD-2", "Service skeleton (health, config, metrics, Docker)",
         "services/chart-decomp-service/\n  app/main.py\n  app/config.py\n  Dockerfile\n  requirements.txt",
         "/health/live, /health/ready,\n/metrics (Prometheus),\npydantic-settings config",
         "M", "Planned", "CD-101",
         "Follow existing service shape (see CLAUDE.md §Service shape). "
         "Port 8011. Add to docker-compose.yml with Traefik label "
         "PathPrefix=/stock_helper/api/v2/chart-decomp."),

        ("CD-202", "CD-2", "Decomposition API endpoints",
         "services/chart-decomp-service/\n  app/api/routes.py",
         "POST /decompose/modwt\nPOST /decompose/emd\nPOST /decompose/eemd\nPOST /decompose/vmd\nPOST /decompose/cwt\nPOST /decompose/hht",
         "M", "Planned", "CD-201,CD-102,CD-103,CD-104,CD-105,CD-106",
         "Request body: {series: float[], params: {...}}. "
         "Response: serialised dataclass (numpy arrays as nested lists or base64 npz). "
         "Validate input length, dtype, NaN (NFR-R1)."),

        ("CD-203", "CD-2", "Hurst & Coherence endpoints",
         "services/chart-decomp-service/\n  app/api/routes.py",
         "POST /hurst\nPOST /coherence",
         "S", "Planned", "CD-201,CD-107,CD-108",
         "Coherence endpoint accepts two series of equal length. "
         "Return COI in response so frontend can overlay it."),

        ("CD-204", "CD-2", "Forecasting & Backtest endpoints + HAR/VMD-HAR engine",
         "services/chart-decomp-service/\n  app/api/routes.py\n  app/services/forecast.py\n  app/services/backtest.py",
         "POST /forecast/har\nPOST /forecast/vmd-har\nPOST /backtest/vol-target\nhar_forecast(), vmd_har_forecast()\nvol_target_backtest()",
         "L", "Planned", "CD-201,CD-109,CD-104",
         "HAR features: [log_rv[t], mean(t-4:t+1), mean(t-21:t+1)]. "
         "VMD-HAR: causal trailing window=1000, edge_lag=5, refit_vmd=20d, refit_model=60d. "
         "NFR-R2: raise exception if fit data includes timestamps ≥ prediction time (Trap B1)."),

        ("CD-205", "CD-2", "CLI: chart-decompose",
         "services/chart-decomp-service/\n  cli.py",
         "chart-decompose decompose\nchart-decompose hurst\nchart-decompose forecast\nchart-decompose backtest",
         "S", "Planned", "CD-202,CD-203,CD-204",
         "Thin CLI that calls the FastAPI service or library directly. "
         "Accept --input CSV, --output npz, --model vmd-har, --target-vol 0.15."),

        # ── Phase CD-3: Frontend Decomposition UI ──────────────────────────────
        ("CD-301", "CD-3", "Route, page layout + sidebar entry + i18n",
         "pages/ChartDecomposition/index.js\nsrc/constants/api.js\nen.json / vi.json\nSidebar.js",
         "React Router /chart-decomposition,\nAPI_ENDPOINTS.CHART_DECOMP,\ni18n keys: chartDecomp.*",
         "S", "Planned", "CD-202",
         "Follow existing page patterns (see TechnicalAnalysis.js for layout reference). "
         "Add nav item under Analysis group in Sidebar. Add EN and VI translations."),

        ("CD-302", "CD-3", "Series input panel (symbol picker + CSV upload)",
         "pages/ChartDecomposition/\n  SeriesInputPanel.js",
         "stock-data-service GET /stocks/{symbol}/prices,\nFileReader API for CSV upload",
         "M", "Planned", "CD-301",
         "Two modes: (1) pick existing stock symbol → fetch daily closes, "
         "(2) upload CSV (date,value columns). "
         "Validate non-empty series before enabling Decompose button."),

        ("CD-303", "CD-3", "MODWT band chart (stacked line charts)",
         "pages/ChartDecomposition/\n  MODWTBandChart.js",
         "recharts ComposedChart or\nd3 multi-panel SVG,\nscale labels: D1 (1-2d) … DJ (64-128d), Approx",
         "L", "Planned", "CD-302,CD-202",
         "One sub-chart per band, same x-axis (date). "
         "Label each band with period range. "
         "Shade COI region in light grey so users see boundary-affected zones."),

        ("CD-304", "CD-3", "CWT scalogram heatmap (log-period y-axis + COI overlay)",
         "pages/ChartDecomposition/\n  CWTScalogram.js",
         "d3 colorScale for |W|²,\nlog-scale y-axis (period),\nCOI as SVG path dashed line",
         "L", "Planned", "CD-302,CD-202",
         "Trap B7: COI is mandatory. Dashed line must clearly separate reliable from "
         "edge-contaminated region. Power colormap: viridis or plasma."),

        ("CD-305", "CD-3", "Hilbert spectrum heatmap",
         "pages/ChartDecomposition/\n  HilbertSpectrum.js",
         "Same heatmap component as CWT scalogram,\nfrequency bins on y-axis",
         "M", "Planned", "CD-302,CD-202",
         "Reuse heatmap rendering from CWTScalogram. "
         "Frequency bins on y-axis (not period). "
         "Tooltip shows instantaneous frequency at cursor."),

        ("CD-306", "CD-3", "Hurst diagnostics panel",
         "pages/ChartDecomposition/\n  HurstDiagnostics.js",
         "recharts ScatterChart,\nlog-log axes,\nLinearRegression fit line",
         "M", "Planned", "CD-302,CD-203",
         "Plot Var(d_j) vs scale j on log-log axes. "
         "Overlay fitted line. Show Ĥ ± SE as prominent readout. "
         "Explain interpretation: H<0.5=mean-revert, H=0.5=random walk, H>0.5=trending."),

        ("CD-307", "CD-3", "Wavelet coherence heatmap with phase arrows",
         "pages/ChartDecomposition/\n  CoherenceHeatmap.js",
         "R² heatmap, phase arrows as SVG,\nthreshold=0.6, arrow directions",
         "M", "Planned", "CD-302,CD-203",
         "Second series picker alongside main series. "
         "Phase arrows: right=in-phase, left=anti, up=y-leads, down=x-leads. "
         "Only draw arrows outside COI and where R²>0.6."),

        ("CD-308", "CD-3", "chartDecompService.js API wrapper",
         "src/services/chartDecompService.js",
         "httpClient wrapping all\nPOST /decompose/* and\n/hurst /coherence endpoints",
         "S", "Planned", "CD-301",
         "Follow existing pattern: one class, one method per endpoint. "
         "No direct axios in components. Handle 422 validation errors gracefully."),

        # ── Phase CD-4: Frontend Forecasting & Backtest UI ─────────────────────
        ("CD-401", "CD-4", "HAR vs VMD-HAR forecast chart",
         "pages/ChartDecomposition/\n  ForecastPanel.js",
         "recharts LineChart,\nActuals + HAR + VMD-HAR lines,\nOOS window shaded",
         "M", "Planned", "CD-301,CD-204",
         "Show OOS window shaded in light blue. "
         "Only label VMD-HAR as 'Improves on HAR' if all 3 DM conditions pass (§3.7.3). "
         "Include training burn-in period as greyed-out region."),

        ("CD-402", "CD-4", "OOS metrics comparison table",
         "pages/ChartDecomposition/\n  MetricsTable.js",
         "RMSE, MAE, R², QLIKE, DM-stat,\nconditional colour formatting",
         "S", "Planned", "CD-401",
         "Three columns: Naive / HAR / VMD-HAR. "
         "Green cell when model beats prior column. "
         "Show DM p-value alongside stat; highlight if |DM|>1.96."),

        ("CD-403", "CD-4", "Backtest equity curve chart",
         "pages/ChartDecomposition/\n  BacktestEquityCurve.js",
         "recharts AreaChart,\nNet PnL + Buy-and-hold + Naive vol-target,\nDrawdown shaded",
         "M", "Planned", "CD-301,CD-204",
         "Three series: net PnL (strategy), buy-and-hold, naive vol-target. "
         "Shade max-drawdown period in light red. "
         "Start equity curve at end of training window only."),

        ("CD-404", "CD-4", "Rolling vol chart + strategy metrics card",
         "pages/ChartDecomposition/\n  RollingVolChart.js\n  StrategyMetricsCard.js",
         "30d rolling std of daily PnL,\ntarget ±30% band lines,\nSharpe/MaxDD/turnover/cost-drag",
         "M", "Planned", "CD-403",
         "Rolling vol chart: dashed target line, light-blue band ±30%. "
         "Metrics card: annualized return & vol, Sharpe, MaxDD, avg leverage, "
         "annualized turnover, cost drag."),

        # ── Phase CD-5: Tests ──────────────────────────────────────────────────
        ("CD-501", "CD-5", "Decomposition unit tests (round-trip, edge robustness)",
         "tests/test_decomp.py",
         "MODWT tol=1e-10, EMD tol=1e-6,\nVMD rel_err<0.2,\nN∈{100,257,1024,5000}",
         "S", "Planned", "CD-102,CD-103,CD-104",
         "Test round-trip: sum(components) ≈ x within tolerance. "
         "Test edge robustness: all lengths complete without error. "
         "Test VMD: K modes returned, sorted by ascending center frequency."),

        ("CD-502", "CD-5", "MODWT translation invariance test",
         "tests/test_decomp.py",
         "shift x by k samples → every component shifts by k",
         "S", "Planned", "CD-102",
         "Roll input array by k=17 samples; verify each component shifts by same k. "
         "This is the defining property of MODWT vs DWT."),

        ("CD-503", "CD-5", "Hurst statistical validation (fGn)",
         "tests/test_hurst.py",
         "fbm.fgn(N=4096, H=h, seed=s),\n50 seeds per H, max_err=0.07",
         "M", "Planned", "CD-107",
         "Generate fractional Gaussian noise with known H∈{0.3,0.5,0.7,0.85}. "
         "N=4096 samples, 50 seeds. "
         "Mean absolute estimation error must be ≤ 0.07 at 95% confidence."),

        ("CD-504", "CD-5", "Wavelet coherence validation",
         "tests/test_coherence.py",
         "shared slow factor + independent fast noise,\nR²>0.5 long scales outside decoupling window,\nR²<0.3 inside",
         "M", "Planned", "CD-108",
         "Construct: x = slow_signal + noise_x, y = slow_signal + noise_y. "
         "Introduce decoupling window where slow_signal is replaced by independent series. "
         "Verify R² thresholds as specified in SRS §5.2."),

        ("CD-505", "CD-5", "Causality / look-ahead tests",
         "tests/test_causality.py",
         "no-leakage swap test,\nlook-ahead detector (R²>0.95 sanity check)",
         "M", "Planned", "CD-204",
         "No-leakage: swap target at t' < t with noise; predictions at t' must not change. "
         "Look-ahead detector: deliberate non-causal forecaster must achieve R²>0.95 OOS — "
         "if it doesn't, the test suite itself has a bug."),

        ("CD-506", "CD-5", "End-to-end Heston SV path test",
         "tests/test_e2e_heston.py",
         "2500-day Heston SV path,\nHAR R²≥0.85 OOS,\nrolling vol ±30% of target on ≥70% days,\nVMD-HAR RMSE within ±10% of HAR",
         "L", "Planned", "CD-204,CD-501,CD-505",
         "Mark @pytest.mark.slow — excluded from quick-test.sh. "
         "Generates Heston path with seed for reproducibility. "
         "VMD-HAR guard: RMSE within ±10% of HAR catches accidental look-ahead re-introduction."),
    ]

    for r, (tid, phase_id, task, comp, api_sym, effort, status, deps, notes) in \
            enumerate(tasks, start=5):
        fill = PHASE_FILLS.get(phase_id)
        cell(ws, r, 1, tid, font=Font(name="Calibri", bold=True, size=10, color="1F4E78"))
        cell(ws, r, 2, phase_id, font=PHASE_TITLE_FONT, fill=fill,
             align=Alignment(horizontal="center", vertical="center"))
        cell(ws, r, 3, task, font=BOLD_FONT)
        cell(ws, r, 4, comp, font=MONO_FONT)
        cell(ws, r, 5, api_sym, font=MONO_FONT)
        cell(ws, r, 6, effort, font=BOLD_FONT, fill=EFFORT_FILLS.get(effort),
             align=Alignment(horizontal="center", vertical="center"))
        cell(ws, r, 7, status, fill=STATUS_FILLS.get(status),
             align=Alignment(horizontal="center", vertical="center"))
        cell(ws, r, 8, deps)
        cell(ws, r, 9, notes)
        ws.row_dimensions[r].height = 56

    autosize(ws, [8, 8, 34, 32, 34, 8, 13, 26, 52])
    ws.freeze_panes = "A5"


# ══════════════════════════════════════════════════════════════════════════════
#  Sheet: "CD Architecture"
# ══════════════════════════════════════════════════════════════════════════════
def build_cd_architecture(wb):
    ws = wb.create_sheet("CD Architecture")
    ws.sheet_view.showGridLines = False

    title_block(ws, "Chart Decomposition — Architecture & Data Flow",
                "Component diagram (text) | SRS §2, §3, §4 | 2026-05-27", 6)

    def section(r, title):
        ws.merge_cells(f"A{r}:F{r}")
        c = ws.cell(row=r, column=1, value=title)
        c.font      = Font(name="Calibri", bold=True, size=12, color="FFFFFF")
        c.fill      = HEADER_FILL
        c.alignment = Alignment(horizontal="left", vertical="center")
        c.border    = BORDER
        ws.row_dimensions[r].height = 22

    def row_2col(r, label, content, label_fill=None):
        c1 = ws.cell(row=r, column=1, value=label)
        c1.font      = BOLD_FONT
        c1.border    = BORDER
        c1.alignment = Alignment(vertical="top", wrap_text=True)
        if label_fill: c1.fill = label_fill
        ws.merge_cells(f"B{r}:F{r}")
        c2 = ws.cell(row=r, column=2, value=content)
        c2.font      = MONO_FONT
        c2.border    = BORDER
        c2.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[r].height = 56

    section(4, "1. Component Overview")
    row_2col(5, "Python library\nchart_decomp/",
             "types.py          ← all dataclass result types\n"
             "decomp.py         ← modwt(), emd(), eemd(), vmd()\n"
             "time_freq.py      ← cwt_scalogram(), hilbert_spectrum()\n"
             "hurst.py          ← hurst_wavelet()\n"
             "coherence.py      ← wavelet_coherence()\n"
             "realized_vol.py   ← realized_variance(), realized_vol()\n"
             "pipelines.py      ← hybrid_a(), hybrid_b(), hybrid_c()\n"
             "forecast.py       ← har_forecast(), vmd_har_forecast()\n"
             "backtest.py       ← vol_target_backtest()")
    row_2col(6, "FastAPI service\nchart-decomp-service/\n(port 8011)",
             "main.py           ← lifespan, /health/*, /metrics\n"
             "config.py         ← pydantic-settings\n"
             "api/routes.py     ← POST /decompose/*, /hurst, /coherence,\n"
             "                     /forecast/*, /backtest/vol-target\n"
             "services/         ← thin wrappers calling chart_decomp library\n"
             "cli.py            ← chart-decompose CLI entry point\n"
             "Dockerfile + requirements.txt")
    row_2col(7, "React frontend\nChartDecomposition/",
             "index.js                ← page layout, tabs\n"
             "SeriesInputPanel.js     ← symbol picker + CSV upload\n"
             "MODWTBandChart.js       ← stacked band line charts\n"
             "CWTScalogram.js         ← heatmap + COI overlay\n"
             "HilbertSpectrum.js      ← Hilbert spectrum heatmap\n"
             "HurstDiagnostics.js     ← log-log variance + Ĥ readout\n"
             "CoherenceHeatmap.js     ← R² heatmap + phase arrows\n"
             "ForecastPanel.js        ← HAR vs VMD-HAR line chart\n"
             "MetricsTable.js         ← RMSE/MAE/R²/QLIKE/DM table\n"
             "BacktestEquityCurve.js  ← net PnL equity curve\n"
             "RollingVolChart.js      ← 30d rolling vol vs target\n"
             "StrategyMetricsCard.js  ← Sharpe, MaxDD, turnover, cost drag\n"
             "chartDecompService.js   ← API wrapper (services/)")

    section(9, "2. Data Flow")
    row_2col(10, "Decomposition\nrequest",
             "Browser → POST /stock_helper/api/v2/chart-decomp/decompose/modwt\n"
             "         body: { series: [float, …], wavelet: 'sym8', level: 6 }\n"
             "Traefik → chart-decomp-service:8011\n"
             "Service → chart_decomp.modwt() → MODWTResult\n"
             "Response: { approximation: [], details: [[],[],…], coi_widths: [], wavelet, level }")
    row_2col(11, "Forecast\nrequest",
             "Browser → POST /stock_helper/api/v2/chart-decomp/forecast/vmd-har\n"
             "         body: { log_rv: [float, …], K: 4, alpha: 1500, window: 1000, … }\n"
             "Service → chart_decomp.vmd_har_forecast()  [causal walk-forward]\n"
             "Response: ForecastResult { timestamps, predictions, actuals, metrics, features_used }")
    row_2col(12, "Backtest\nrequest",
             "Browser → POST /stock_helper/api/v2/chart-decomp/backtest/vol-target\n"
             "         body: { returns: [], vol_forecast: [], target_ann_vol: 0.15, … }\n"
             "Service → chart_decomp.vol_target_backtest()\n"
             "Response: BacktestResult { pnl_gross, pnl_net, positions, turnover, metrics }")

    section(14, "3. Key Design Constraints (from SRS §2.5)")
    constraints = [
        ("C1 Strict causality",
         "Forecasting module MUST NOT decompose the full series and slice. "
         "Use only data up to prediction time. vmd_har_forecast() applies VMD on a trailing "
         "window [t-WINDOW, t]. NFR-R2 raises exception if fit includes future timestamps."),
        ("C2 Boundary handling",
         "All time-freq views return COI as a 1-D array. "
         "Frontend MUST overlay COI on every CWT scalogram, HHT spectrum, and coherence plot. "
         "Do not render edge-contaminated regions as reliable analysis."),
        ("C3 Mode-ordering stability",
         "VMD modes are sorted by ascending center frequency at every call and every refit. "
         "Without this, the feature vector silently changes meaning between VMD refits."),
        ("C4 Benchmark gating",
         "Forecast UI must always show Naive and HAR side-by-side with any candidate model. "
         "'Improves on HAR' label requires ΔRMSE>0 AND ΔQLIKE>0 AND |DM|>1.96."),
        ("C5 Reproducibility",
         "eemd(), synthetic data generators, and Heston SV test all accept seed=. "
         "Library logs its version + dependency versions in any saved ForecastResult."),
    ]
    for r_off, (label, text) in enumerate(constraints, start=15):
        row_2col(r_off, label, text,
                 label_fill=PatternFill("solid", fgColor="DDEBF7"))

    section(21, "4. Service Registration Checklist")
    checklist = [
        ("docker-compose.yml",    "Add chart-decomp-service block, port 8011, health-check on /health/live"),
        ("Traefik labels",        "PathPrefix=/stock_helper/api/v2/chart-decomp → chart-decomp-service:8011"),
        ("constants/api.js",     "Add CHART_DECOMP_BASE and per-endpoint constants"),
        ("chartDecompService.js", "One method per endpoint; wrap httpClient; no axios in components"),
        ("Sidebar.js",           "Add nav entry under Analysis group, use i18n key chartDecomp.nav"),
        ("en.json / vi.json",    "Add chartDecomp.* i18n keys for all labels, tooltips, axis titles"),
        ("CLAUDE.md gateway map","Add /chart-decomp → chart-decomp-service row to routing table"),
    ]
    for r_off, (component, note) in enumerate(checklist, start=22):
        row_2col(r_off, component, note)

    autosize(ws, [24, 80])
    ws.column_dimensions["A"].width = 24
    ws.freeze_panes = "A4"


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    wb = load_workbook(XLSX)

    # Remove old CD sheets if re-running
    for sheet_name in ["CD Overview", "CD Tasks", "CD Architecture"]:
        if sheet_name in wb.sheetnames:
            del wb[sheet_name]

    build_cd_overview(wb)
    build_cd_tasks(wb)
    build_cd_architecture(wb)

    wb.save(XLSX)
    print(f"Saved → {XLSX}")
    print(f"Sheets now: {wb.sheetnames}")
