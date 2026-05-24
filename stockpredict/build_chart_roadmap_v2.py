"""Generate roadmap_version_2.xlsx — Chart feature roadmap (phases 2-6).
Run: python3 build_chart_roadmap_v2.py
"""
from __future__ import annotations
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = "/home/tuanph/all_projects/stockpredict/roadmap_version_2.xlsx"

# ── Styles ────────────────────────────────────────────────────────────────────
THIN   = Side(style="thin",   color="BFBFBF")
MEDIUM = Side(style="medium", color="9E9E9E")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BORDER_THICK_TOP = Border(left=THIN, right=THIN, top=MEDIUM, bottom=THIN)

HEADER_FILL     = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT     = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
TITLE_FONT      = Font(name="Calibri", bold=True, size=16, color="1F4E78")
SUBTITLE_FONT   = Font(name="Calibri", italic=True, size=10, color="595959")
PHASE_TITLE_FONT= Font(name="Calibri", bold=True, size=12, color="FFFFFF")
DONE_FONT       = Font(name="Calibri", size=10, color="375623", bold=True)
NORMAL_FONT     = Font(name="Calibri", size=10)
LINK_FONT       = Font(name="Calibri", size=10, color="0563C1", underline="single")

STATUS_FILLS = {
    "Done":         PatternFill("solid", fgColor="C6EFCE"),
    "In Progress":  PatternFill("solid", fgColor="FFEB9C"),
    "Planned":      PatternFill("solid", fgColor="DDEBF7"),
    "Not Started":  PatternFill("solid", fgColor="F2F2F2"),
    "Blocked":      PatternFill("solid", fgColor="FFC7CE"),
}

PHASE_FILLS = {
    1: PatternFill("solid", fgColor="1F4E78"),  # navy  (Done)
    2: PatternFill("solid", fgColor="2E75B6"),  # blue
    3: PatternFill("solid", fgColor="375623"),  # green
    4: PatternFill("solid", fgColor="7030A0"),  # purple
    5: PatternFill("solid", fgColor="C55A11"),  # orange
    6: PatternFill("solid", fgColor="404040"),  # dark grey (future)
}

EFFORT_FILLS = {
    "S":  PatternFill("solid", fgColor="E2EFDA"),
    "M":  PatternFill("solid", fgColor="FFEB9C"),
    "L":  PatternFill("solid", fgColor="FCE4D6"),
    "XL": PatternFill("solid", fgColor="FFC7CE"),
}

def col(ws, row, c, value, font=None, fill=None, align=None, border=True):
    cell = ws.cell(row=row, column=c, value=value)
    cell.font   = font  or NORMAL_FONT
    if fill:   cell.fill   = fill
    if border: cell.border = BORDER
    cell.alignment = align or Alignment(vertical="top", wrap_text=True)
    return cell

def header_row(ws, row, headers, fill=None):
    for i, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=i, value=h)
        cell.fill  = fill or HEADER_FILL
        cell.font  = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER

def autosize(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


# ══════════════════════════════════════════════════════════════════════════════
#  Sheet 1 — Phase Overview
# ══════════════════════════════════════════════════════════════════════════════
def build_overview(wb):
    ws = wb.create_sheet("Phase Overview")
    ws.sheet_view.showGridLines = False

    # Title
    ws.merge_cells("A1:G1")
    c = ws["A1"]
    c.value = "StockPredict — Chart Roadmap v2"
    c.font  = TITLE_FONT
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    ws.merge_cells("A2:G2")
    c = ws["A2"]
    c.value = "Phases 1–6  |  Focus: StockChart.js  |  As of 2026-05-24"
    c.font  = SUBTITLE_FONT
    c.alignment = Alignment(horizontal="center", vertical="center")

    headers = ["Phase", "Name", "Key Deliverables", "Primary File(s)", "Effort", "Status", "Notes"]
    header_row(ws, 4, headers)

    phases = [
        (1, "Foundation ✅",
         "• Responsive width (ResizeObserver)\n• MACD pane (replaces Elder Ray)\n• RSI overlay on price pane — right Y-axis\n• Indicator toggle dropdown (6 checkboxes)\n• Volume pane at bottom",
         "StockChart.js", "L", "Done",
         "Completed 2026-05-24. All 4 panes in one ChartCanvas."),
        (2, "Overlay Indicators",
         "• Bollinger Bands (upper/mid/lower on price pane)\n• VWAP line on price pane\n• Custom-period SMA selector\n• Add 3 new items to dropdown",
         "StockChart.js\nchartTheme.js", "M", "Planned",
         "All use LineSeries / BollingerSeries — same pane, same price scale. No new pane needed."),
        (3, "More Oscillators",
         "• Stochastic Oscillator (%K, %D) — new pane\n• ATR (Average True Range) — new pane\n• Pane height adjusts dynamically when toggled\n• Add to dropdown",
         "StockChart.js", "M", "Planned",
         "react-financial-charts has stochasticOscillator() and atr() calculators + series."),
        (4, "Interactive Drawing Tools",
         "• Trend line (click-drag)\n• Horizontal support/resistance line\n• Fibonacci retracement tool\n• Toolbar to select draw mode / clear all",
         "StockChart.js\nDrawingToolbar.js (new)", "L", "Planned",
         "Uses @react-financial-charts/interactive (TrendLine, FibonacciRetracement, etc). Coordinates saved in component state."),
        (5, "Chart Enhancements",
         "• Timeframe tabs: 1M / 3M / 6M / 1Y / All\n• Candlestick type toggle: Candle / Heikin-Ashi / OHLC Bar\n• Save indicator preferences to localStorage\n• Crosshair tooltip showing all active values",
         "StockChart.js\nAIInsights.js\nTechnicalAnalysis.js", "M", "Planned",
         "Heikin-Ashi uses heikinAshi() calculator. localStorage key per stock symbol."),
        (6, "Multi-stock Comparison (Future)",
         "• Overlay a second stock as a % return line\n• Colour-coded legend\n• Comparator symbol picker",
         "StockChart.js", "XL", "Not Started",
         "Lower priority — requires normalising two price series to % return from start date."),
    ]

    for r, (ph, name, deliverables, files, effort, status, notes) in enumerate(phases, start=5):
        col(ws, r, 1, f"Phase {ph}", font=PHASE_TITLE_FONT, fill=PHASE_FILLS[ph],
            align=Alignment(horizontal="center", vertical="center"))
        col(ws, r, 2, name, font=Font(name="Calibri", bold=True, size=11))
        col(ws, r, 3, deliverables)
        col(ws, r, 4, files)
        col(ws, r, 5, effort, font=Font(name="Calibri", bold=True, size=10),
            fill=EFFORT_FILLS.get(effort), align=Alignment(horizontal="center", vertical="center"))
        status_cell = col(ws, r, 6, status, fill=STATUS_FILLS.get(status, None),
                          align=Alignment(horizontal="center", vertical="center"))
        if status == "Done":
            status_cell.font = DONE_FONT
        col(ws, r, 7, notes)
        ws.row_dimensions[r].height = 80

    autosize(ws, [10, 22, 52, 28, 8, 14, 48])
    ws.freeze_panes = "A5"

    # Effort legend
    legend_row = len(phases) + 7
    ws.cell(row=legend_row, column=1, value="Effort key:").font = Font(name="Calibri", bold=True, size=9)
    for i, (k, label) in enumerate([("S","< 2 h"),("M","2–4 h"),("L","4–8 h"),("XL","> 8 h")], start=2):
        c = ws.cell(row=legend_row, column=i, value=f"{k} = {label}")
        c.fill = EFFORT_FILLS[k]
        c.font = Font(name="Calibri", size=9)
        c.border = BORDER
        c.alignment = Alignment(horizontal="center")


# ══════════════════════════════════════════════════════════════════════════════
#  Sheet 2 — Detailed Task List
# ══════════════════════════════════════════════════════════════════════════════
def build_tasks(wb):
    ws = wb.create_sheet("Chart Tasks")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:I1")
    c = ws["A1"]
    c.value = "Chart Tasks — Detailed"
    c.font  = TITLE_FONT
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    headers = ["ID", "Phase", "Task", "Component / File", "API / Symbol", "Effort", "Status", "Depends On", "Notes"]
    header_row(ws, 3, headers)

    tasks = [
        # ── Phase 1 (Done) ────────────────────────────────────────────────────
        ("C-101", "1 ✅", "Responsive chart width via ResizeObserver",        "StockChart.js",          "useRef, ResizeObserver",              "S", "Done",        "",      "containerRef + useState(chartWidth)"),
        ("C-102", "1 ✅", "Replace Elder Ray pane with MACD pane",            "StockChart.js",          "macd(), MACDSeries, MACDTooltip",     "S", "Done",        "",      "fast=12 slow=26 signal=9; MACD_APPEARANCE constant"),
        ("C-103", "1 ✅", "RSI (14) overlay on price pane, right Y-axis",     "StockChart.js",          "rsi(), RSISeries, RSITooltip",        "S", "Done",        "",      "Chart id=2 at origin=[0,0] yExtents=[0,100]; axisAt=right"),
        ("C-104", "1 ✅", "Indicator toggle dropdown (6 checkboxes)",          "StockChart.js",          "useState(indicators), ResizeObserver","M", "Done",        "",      "Dropdown closes on outside click; pane heights shrink dynamically"),
        ("C-105", "1 ✅", "Dynamic canvas height when panes toggled",          "StockChart.js",          "macdHeight/volHeight conditional",    "S", "Done",        "C-104", "Height = priceH + macdH + volH; recalc on each render"),

        # ── Phase 2 ───────────────────────────────────────────────────────────
        ("C-201", "2",    "Bollinger Bands on price pane",                    "StockChart.js",          "bollingerBand(), BollingerSeries",    "S", "Planned",     "",      "Upper/mid/lower LineSeries; add 'BB (20,2)' checkbox"),
        ("C-202", "2",    "VWAP line on price pane",                          "StockChart.js",          "No built-in — compute manually",      "M", "Planned",     "",      "VWAP = cumSum(price*vol)/cumSum(vol); reset daily; draw as LineSeries"),
        ("C-203", "2",    "Custom SMA period input",                          "StockChart.js",          "sma(), LineSeries",                   "S", "Planned",     "",      "Small number input in dropdown alongside SMA checkbox; default period 20"),
        ("C-204", "2",    "Add Phase 2 indicators to dropdown",               "StockChart.js",          "INDICATOR_OPTIONS array",             "S", "Planned",     "C-201,C-202,C-203", "Append BB, VWAP, SMA to INDICATOR_OPTIONS; same toggle pattern"),

        # ── Phase 3 ───────────────────────────────────────────────────────────
        ("C-301", "3",    "Stochastic Oscillator pane (%K / %D)",             "StockChart.js",          "stochasticOscillator(), StoSeries",   "M", "Planned",     "",      "Separate pane; reference lines at 20/80; add to dropdown"),
        ("C-302", "3",    "ATR (Average True Range) pane",                    "StockChart.js",          "atr(), AreaOnlySeries or LineSeries", "S", "Planned",     "",      "Separate pane; no fixed scale — yExtents auto; shows volatility"),
        ("C-303", "3",    "Pane ordering & height config object",             "StockChart.js",          "paneConfig array",                    "M", "Planned",     "C-301,C-302", "Refactor hardcoded heights into a paneConfig[] so new panes slot in cleanly"),

        # ── Phase 4 ───────────────────────────────────────────────────────────
        ("C-401", "4",    "Trend line drawing tool",                          "StockChart.js\nDrawingToolbar.js", "TrendLine (interactive pkg)", "M", "Planned",     "",      "react-financial-charts/interactive; state array of drawn lines"),
        ("C-402", "4",    "Horizontal S/R line tool",                        "StockChart.js",          "GannFan or StraightLine interactive", "S", "Planned",     "C-401", "Click to place; drag to move; right-click to delete"),
        ("C-403", "4",    "Fibonacci retracement tool",                      "StockChart.js",          "FibonacciRetracement (interactive)",  "M", "Planned",     "C-401", "Click high → drag to low; auto-draws 23.6 / 38.2 / 50 / 61.8 levels"),
        ("C-404", "4",    "Drawing toolbar UI",                              "DrawingToolbar.js (new)","React state: activeTool",             "M", "Planned",     "C-401,C-402,C-403", "Icon buttons: cursor / trend / H-line / Fib / eraser; highlighted when active"),

        # ── Phase 5 ───────────────────────────────────────────────────────────
        ("C-501", "5",    "Timeframe selector tabs (1M/3M/6M/1Y/All)",       "AIInsights.js\nTechnicalAnalysis.js", "slice(data, -N)",         "S", "Planned",     "",      "xExtents clipped server-side or client-side slice; pass as prop or internal state"),
        ("C-502", "5",    "Candlestick type toggle (Candle/Heikin-Ashi/Bar)","StockChart.js",          "heikinAshi(), CandlestickSeries, OHLCSeries", "M","Planned","",  "heikinAshi() calc transforms OHLC; swap series component based on toggle"),
        ("C-503", "5",    "Persist indicator prefs in localStorage",         "StockChart.js",          "localStorage.getItem/setItem",        "S", "Planned",     "C-104", "Key: `stockchart_indicators_${symbol}`; load on mount, save on change"),
        ("C-504", "5",    "Unified crosshair tooltip (all values)",          "StockChart.js",          "OHLCTooltip + custom SVG tooltip",    "M", "Planned",     "",      "Custom tooltip component overlaying OHLC, EMA12/26, RSI, MACD at cursor position"),

        # ── Phase 6 ───────────────────────────────────────────────────────────
        ("C-601", "6",    "Second-stock % return overlay",                   "StockChart.js",          "compare() indicator",                 "XL","Not Started",  "",      "Normalise both series to 100 at start date; LineSeries on right axis"),
        ("C-602", "6",    "Comparator symbol picker UI",                     "StockChart.js",          "ComparatorSelector component",        "M", "Not Started",  "C-601", "Dropdown to pick comparison ticker; shows coloured legend"),
    ]

    for r, row in enumerate(tasks, start=4):
        tid, phase, task, comp, api, effort, status, deps, notes = row
        col(ws, r, 1, tid,    font=Font(name="Calibri", bold=True, size=10, color="1F4E78"))
        ph_num = int(phase[0])
        col(ws, r, 2, phase,  fill=PHASE_FILLS.get(ph_num), font=PHASE_TITLE_FONT,
            align=Alignment(horizontal="center", vertical="center"))
        col(ws, r, 3, task)
        col(ws, r, 4, comp)
        col(ws, r, 5, api)
        col(ws, r, 6, effort, fill=EFFORT_FILLS.get(effort),
            align=Alignment(horizontal="center", vertical="center"),
            font=Font(name="Calibri", bold=True, size=10))
        col(ws, r, 7, status, fill=STATUS_FILLS.get(status),
            align=Alignment(horizontal="center", vertical="center"))
        col(ws, r, 8, deps)
        col(ws, r, 9, notes)
        ws.row_dimensions[r].height = 36

    autosize(ws, [8, 8, 40, 28, 32, 8, 13, 16, 48])
    ws.freeze_panes = "A4"


# ══════════════════════════════════════════════════════════════════════════════
#  Sheet 3 — Session Log
# ══════════════════════════════════════════════════════════════════════════════
def build_session_log(wb):
    ws = wb.create_sheet("Session Log")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value = "Session Log"
    c.font  = TITLE_FONT
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    headers = ["Date", "Phase(s) Touched", "Tasks Completed", "Files Changed", "Where I Left Off", "Next Session Start"]
    header_row(ws, 3, headers)

    log = [
        ("2026-05-24",
         "Phase 1",
         "C-101 Responsive width\nC-102 MACD pane\nC-103 RSI overlay right-axis\nC-104 Indicator dropdown\nC-105 Dynamic canvas height",
         "StockChart.js\nnginx.conf (cache fix)\nSidebar.js / MainLayout.js (Decision Helper Overview)\nen.json / vi.json",
         "All Phase 1 chart tasks done.\nFrontend rebuilt & deployed to Docker (port 3004).\nnginx cache-control fix committed.",
         "Start Phase 2: Bollinger Bands (C-201)\n→ import bollingerBand from react-financial-charts\n→ add BollingerSeries to price Chart (id=1)\n→ add 'BB (20,2)' to INDICATOR_OPTIONS"),
    ]

    for r, row in enumerate(log, start=4):
        date, phases, done, files, left_off, next_start = row
        col(ws, r, 1, date,   font=Font(name="Calibri", bold=True, size=10))
        col(ws, r, 2, phases)
        col(ws, r, 3, done)
        col(ws, r, 4, files)
        col(ws, r, 5, left_off, fill=PatternFill("solid", fgColor="FFEB9C"))
        col(ws, r, 6, next_start, fill=PatternFill("solid", fgColor="DDEBF7"))
        ws.row_dimensions[r].height = 80

    # Blank rows for future sessions
    for r in range(len(log) + 4, len(log) + 10):
        for c_idx in range(1, 7):
            cell = ws.cell(row=r, column=c_idx, value="")
            cell.border = BORDER
        ws.row_dimensions[r].height = 60

    autosize(ws, [13, 18, 42, 32, 48, 44])
    ws.freeze_panes = "A4"


# ══════════════════════════════════════════════════════════════════════════════
#  Sheet 4 — Quick Reference (API cheat-sheet)
# ══════════════════════════════════════════════════════════════════════════════
def build_reference(wb):
    ws = wb.create_sheet("API Reference")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:E1")
    c = ws["A1"]
    c.value = "react-financial-charts v2 — Indicators Quick Reference"
    c.font  = TITLE_FONT
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    headers = ["Indicator", "Calculator Import", "Series Component", "Tooltip", "Notes"]
    header_row(ws, 3, headers)

    refs = [
        ("EMA",              "ema()",                  "LineSeries",          "MovingAverageTooltip",  "Done ✅"),
        ("SAR",              "sar()",                  "SARSeries",           "—",                     "Done ✅"),
        ("MACD",             "macd()",                 "MACDSeries",          "MACDTooltip",           "Done ✅  Need appearance prop"),
        ("RSI",              "rsi()",                  "RSISeries",           "RSITooltip",            "Done ✅  Need displayFormat prop"),
        ("Bollinger Bands",  "bollingerBand()",        "BollingerSeries",     "BollingerBandTooltip",  "Phase 2"),
        ("SMA",              "sma()",                  "LineSeries",          "MovingAverageTooltip",  "Phase 2"),
        ("Stochastic",       "stochasticOscillator()", "StochasticSeries",    "StochasticTooltip",     "Phase 3  — check exact export name"),
        ("ATR",              "atr()",                  "AreaOnlySeries",      "SingleValueTooltip",    "Phase 3"),
        ("Heikin-Ashi",      "heikinAshi()",           "CandlestickSeries",   "OHLCTooltip",           "Phase 5  — transforms OHLC data"),
        ("VWAP",             "manual (no built-in)",   "LineSeries",          "SingleValueTooltip",    "Phase 2  — compute in data layer"),
        ("Trend Line",       "—",                      "TrendLine",           "—",                     "Phase 4  — from interactive package"),
        ("Fibonacci",        "—",                      "FibonacciRetracement","—",                     "Phase 4  — from interactive package"),
    ]

    for r, row in enumerate(refs, start=4):
        ind, calc, series, tooltip, notes = row
        col(ws, r, 1, ind,     font=Font(name="Calibri", bold=True, size=10))
        col(ws, r, 2, calc,    font=Font(name="Calibri", size=10, color="0563C1"))
        col(ws, r, 3, series,  font=Font(name="Calibri", size=10, color="375623"))
        col(ws, r, 4, tooltip)
        done_fill = STATUS_FILLS["Done"] if "Done" in notes else (
                    STATUS_FILLS["Planned"] if "Phase" in notes else None)
        col(ws, r, 5, notes,   fill=done_fill)
        ws.row_dimensions[r].height = 22

    autosize(ws, [20, 28, 26, 26, 36])
    ws.freeze_panes = "A4"


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    wb = Workbook()
    wb.remove(wb.active)   # remove default "Sheet"

    build_overview(wb)
    build_tasks(wb)
    build_session_log(wb)
    build_reference(wb)

    wb.save(OUT)
    print(f"Saved → {OUT}")
