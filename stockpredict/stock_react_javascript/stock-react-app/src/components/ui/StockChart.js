
import React, { useRef, useEffect, useState, useMemo } from "react";
import { format } from "d3-format";
import { timeFormat } from "d3-time-format";
import { getXAxisProps, getYAxisProps, chartColors, chartMargin } from "../../constants/chartTheme";
import ChartWrapper from "./ChartWrapper";

import {
  ema,
  sma,
  sar,
  rsi,
  macd,
  bollingerBand,
  stochasticOscillator,
  atr,
  discontinuousTimeScaleProviderBuilder,
  Chart,
  ChartCanvas,
  BarSeries,
  CandlestickSeries,
  OHLCSeries,
  SARSeries,
  LineSeries,
  RSISeries,
  MACDSeries,
  BollingerSeries,
  StochasticSeries,
  MovingAverageTooltip,
  OHLCTooltip,
  RSITooltip,
  MACDTooltip,
  BollingerBandTooltip,
  StochasticTooltip,
  SingleValueTooltip,
  HoverTooltip,
  lastVisibleItemBasedZoomAnchor,
  XAxis,
  YAxis,
  CrossHairCursor,
  EdgeIndicator,
  MouseCoordinateX,
  MouseCoordinateY,
  ZoomButtons,
} from "react-financial-charts";

const MACD_APPEARANCE = {
  strokeStyle: { macd: "#2196f3", signal: "#ff9800", zero: "#6B7280" },
  fillStyle:   { divergence: "rgba(33,150,243,0.3)" },
};

const BB_APPEARANCE = {
  stroke:  { top: "#a78bfa", middle: "#8b5cf6", bottom: "#a78bfa" },
  fill:    "rgba(167,139,250,0.10)",
};

const VWAP_STROKE = "#fbbf24";
const SMA_STROKE  = "#10b981";
const ATR_STROKE  = "#06b6d4";

const SMA_MIN = 2;
const SMA_MAX = 200;

// Pane heights for sub-panes below the price pane.
// Render order top→bottom is the order of keys in this object.
const SUB_PANE_HEIGHTS = {
  macd:   100,
  stoch:  100,
  atr:    80,
  volume: 80,
};

const SUB_PANE_ORDER = Object.keys(SUB_PANE_HEIGHTS);

// Timeframe tabs — slice the most-recent N rows from initialData.
// Approx trading days per period (252 sessions/year).
const TIMEFRAME_OPTIONS = [
  { key: "1M",  rows: 22  },
  { key: "3M",  rows: 66  },
  { key: "6M",  rows: 132 },
  { key: "1Y",  rows: 252 },
  { key: "All", rows: null },
];

const CANDLE_TYPES = [
  { key: "candle",     label: "Candle" },
  { key: "heikinAshi", label: "Heikin-Ashi" },
  { key: "ohlc",       label: "OHLC Bar" },
];

const INDICATOR_DEFAULTS = {
  ema12:  true,
  ema26:  true,
  sar:    true,
  rsi:    true,
  macd:   true,
  stoch:  false,
  atr:    false,
  bb:     false,
  vwap:   false,
  sma:    false,
  volume: true,
};

const LS_KEY_PREFIX = "stockchart_prefs_";

const INDICATOR_OPTIONS = [
  { key: "ema12",  label: "EMA 12" },
  { key: "ema26",  label: "EMA 26" },
  { key: "sar",    label: "Parabolic SAR" },
  { key: "rsi",    label: "RSI (14)" },
  { key: "macd",   label: "MACD (12,26,9)" },
  { key: "stoch",  label: "Stochastic (12,3,3)" },
  { key: "atr",    label: "ATR (14)" },
  { key: "bb",     label: "Bollinger Bands (20,2)" },
  { key: "vwap",   label: "VWAP" },
  { key: "sma",    label: "SMA" },
  { key: "volume", label: "Volume" },
];

// ── Inline styles for the indicator dropdown ─────────────────────────────────

const dropdownStyles = {
  wrapper: {
    position: "absolute",
    top: 8,
    right: 72,   // outside the right Y-axis margin
    zIndex: 20,
  },
  button: {
    padding: "4px 10px",
    fontSize: 12,
    fontFamily: "Inter, sans-serif",
    background: "#1F2937",
    color: "#D1D5DB",
    border: "1px solid #374151",
    borderRadius: 4,
    cursor: "pointer",
    userSelect: "none",
  },
  panel: {
    position: "absolute",
    right: 0,
    top: "calc(100% + 4px)",
    background: "#1F2937",
    border: "1px solid #374151",
    borderRadius: 6,
    padding: "8px 12px",
    minWidth: 170,
    boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "4px 0",
    cursor: "pointer",
    color: "#D1D5DB",
    fontSize: 12,
    fontFamily: "Inter, sans-serif",
    userSelect: "none",
  },
  checkbox: {
    accentColor: "#3B82F6",
    cursor: "pointer",
  },
  periodInput: {
    width: 48,
    marginLeft: "auto",
    background: "#111827",
    color: "#D1D5DB",
    border: "1px solid #374151",
    borderRadius: 3,
    padding: "1px 4px",
    fontSize: 11,
    fontFamily: "Inter, sans-serif",
  },
};

const headerStyles = {
  bar: {
    position: "absolute",
    top: 8,
    left: 8,
    zIndex: 20,
    display: "flex",
    gap: 12,
    alignItems: "center",
    fontFamily: "Inter, sans-serif",
  },
  group: {
    display: "flex",
    gap: 2,
    background: "#1F2937",
    border: "1px solid #374151",
    borderRadius: 4,
    padding: 2,
  },
  tab: (active) => ({
    padding: "3px 8px",
    fontSize: 11,
    background: active ? "#3B82F6" : "transparent",
    color: active ? "#F9FAFB" : "#9CA3AF",
    border: "none",
    borderRadius: 3,
    cursor: "pointer",
    userSelect: "none",
  }),
};

// ─────────────────────────────────────────────────────────────────────────────

export default function StockChart({ initialData, symbol }) {
  const containerRef   = useRef(null);
  const dropdownRef    = useRef(null);
  const hydratedRef    = useRef(false);
  const [chartWidth,   setChartWidth]   = useState(900);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [indicators,   setIndicators]   = useState(INDICATOR_DEFAULTS);
  const [smaPeriod,    setSmaPeriod]    = useState(20);
  const [timeframe,    setTimeframe]    = useState("All");
  const [candleType,   setCandleType]   = useState("candle");

  const lsKey = `${LS_KEY_PREFIX}${symbol || "default"}`;

  // Load saved prefs when symbol (and thus lsKey) changes.
  useEffect(() => {
    hydratedRef.current = false;
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(lsKey) || "null"); } catch { /* ignore */ }
    setIndicators(saved?.indicators
      ? { ...INDICATOR_DEFAULTS, ...saved.indicators }
      : INDICATOR_DEFAULTS
    );
    setSmaPeriod(Number.isFinite(saved?.smaPeriod) ? saved.smaPeriod : 20);
    setTimeframe(saved?.timeframe || "All");
    setCandleType(saved?.candleType || "candle");
    hydratedRef.current = true;
  }, [lsKey]);

  // Persist whenever any pref changes (after the initial hydrate has run).
  useEffect(() => {
    if (!hydratedRef.current) return;
    try {
      localStorage.setItem(lsKey, JSON.stringify({
        indicators, smaPeriod, timeframe, candleType,
      }));
    } catch { /* ignore quota errors */ }
  }, [lsKey, indicators, smaPeriod, timeframe, candleType]);

  // Responsive width
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const w = Math.floor(entries[0].contentRect.width);
      if (w > 0) setChartWidth(w);
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownOpen]);

  const toggle = (key) => setIndicators((prev) => ({ ...prev, [key]: !prev[key] }));

  // ── Indicator calculators ───────────────────────────────────────────────────

  const ScaleProvider = discontinuousTimeScaleProviderBuilder().inputDateAccessor(
    (d) => new Date(d.time)
  );

  const margin = { ...chartMargin, right: 64 };

  const priceHeight = 400;

  // Sub-pane layout: compute origin y-offsets and total height from the
  // currently-enabled sub-panes, in SUB_PANE_ORDER. The bottom-most enabled
  // sub-pane is the one that shows the X-axis tick labels.
  const paneOrigin = {};
  let _paneY = priceHeight;
  let lastEnabledSubPaneKey = null;
  for (const key of SUB_PANE_ORDER) {
    if (!indicators[key]) continue;
    paneOrigin[key] = _paneY;
    _paneY += SUB_PANE_HEIGHTS[key];
    lastEnabledSubPaneKey = key;
  }
  const totalHeight = _paneY + margin.top + margin.bottom;
  const isBottomSubPane = (key) => key === lastEnabledSubPaneKey;

  const ema12 = ema()
    .id(1)
    .options({ windowSize: 12 })
    .merge((d, c) => { d.ema12 = c; })
    .accessor((d) => d.ema12);

  const ema26 = ema()
    .id(2)
    .options({ windowSize: 26 })
    .merge((d, c) => { d.ema26 = c; })
    .accessor((d) => d.ema26);

  const defaultSar = sar()
    .options({ accelerationFactor: 0.02, maxAccelerationFactor: 0.2 })
    .merge((d, c) => { d.sar = c; })
    .accessor((d) => d.sar);

  const rsiCalc = rsi()
    .options({ windowSize: 14 })
    .merge((d, c) => { d.rsi = c; })
    .accessor((d) => d.rsi);

  const macdCalc = macd()
    .options({ fast: 12, slow: 26, signal: 9 })
    .merge((d, c) => { d.macd = c; })
    .accessor((d) => d.macd);

  const bbCalc = bollingerBand()
    .options({ windowSize: 20, multiplier: 2, movingAverageType: "sma", sourcePath: "close" })
    .merge((d, c) => { d.bb = c; })
    .accessor((d) => d.bb)
    .stroke(BB_APPEARANCE.stroke)
    .fill(BB_APPEARANCE.fill);

  const smaCalc = sma()
    .id(99)
    .options({ windowSize: smaPeriod, sourcePath: "close" })
    .merge((d, c) => { d.smaCustom = c; })
    .accessor((d) => d.smaCustom);

  const stochCalc = stochasticOscillator()
    .options({ windowSize: 12, kWindowSize: 3, dWindowSize: 3 })
    .merge((d, c) => { d.stoch = c; })
    .accessor((d) => d.stoch);

  const atrCalc = atr()
    .options({ windowSize: 14 })
    .merge((d, c) => { d.atr = c; })
    .accessor((d) => d.atr);

  // Timeframe slice — take the most-recent N rows (or all).
  const sourceData = useMemo(() => {
    const tf = TIMEFRAME_OPTIONS.find((t) => t.key === timeframe);
    if (!tf || tf.rows == null || !initialData?.length) return initialData || [];
    return initialData.slice(Math.max(0, initialData.length - tf.rows));
  }, [initialData, timeframe]);

  const calculatedData = atrCalc(
    stochCalc(smaCalc(bbCalc(macdCalc(rsiCalc(defaultSar(ema26(ema12(sourceData))))))))
  );

  // VWAP — anchored cumulative from start of dataset (typical price * volume)
  // Compute against real OHLC so HA mode doesn't distort the anchor.
  let cumPV = 0;
  let cumV  = 0;
  for (const row of calculatedData) {
    const tp  = (row.high + row.low + row.close) / 3;
    const vol = row.volume || 0;
    cumPV += tp * vol;
    cumV  += vol;
    row.vwap = cumV > 0 ? cumPV / cumV : tp;
  }

  // Heikin-Ashi values — computed from real OHLC and stored in separate
  // fields so toggling between candle types is non-destructive. Standard
  // formulas: haClose = avg of OHLC; haOpen seeded with (open+close)/2.
  let prevHaOpen = 0, prevHaClose = 0;
  for (let i = 0; i < calculatedData.length; i++) {
    const d = calculatedData[i];
    const haClose = (d.open + d.high + d.low + d.close) / 4;
    const haOpen  = i === 0 ? (d.open + d.close) / 2 : (prevHaOpen + prevHaClose) / 2;
    d.haOpen  = haOpen;
    d.haClose = haClose;
    d.haHigh  = Math.max(d.high, haOpen, haClose);
    d.haLow   = Math.min(d.low,  haOpen, haClose);
    prevHaOpen  = haOpen;
    prevHaClose = haClose;
  }

  const { data, xScale, xAccessor, displayXAccessor } = ScaleProvider(calculatedData);

  const priceFormat  = format(".2f");
  const volumeFormat = format(".2s");
  const dateFormat   = timeFormat("%d %b");

  // When a specific timeframe is selected, fit the whole sliced range into the
  // initial view. For "All", fall back to the most-recent 100-row window.
  const initialWindow = timeframe === "All" ? 100 : data.length;
  const max = xAccessor(data[data.length - 1]);
  const min = xAccessor(data[Math.max(0, data.length - initialWindow)]);
  const xExtents = [min, max + 5];

  // Visible OHLC depends on candleType — Heikin-Ashi uses computed HA fields,
  // everything else reads the real OHLC.
  const isHA = candleType === "heikinAshi";
  const visibleOHLC = isHA
    ? (d) => ({ open: d.haOpen, high: d.haHigh, low: d.haLow, close: d.haClose })
    : (d) => ({ open: d.open,   high: d.high,   low: d.low,   close: d.close });

  const volumeColor    = (d) => d.close > d.open ? chartColors.greenVolume  : chartColors.redVolume;
  const openCloseColor = (d) => {
    const o = visibleOHLC(d);
    return o.close > o.open ? chartColors.greenCandle : chartColors.redCandle;
  };

  // tooltip entries depend on which moving averages are active
  const maTooltipOptions = [
    indicators.ema26 && { yAccessor: ema26.accessor(), type: "EMA", stroke: ema26.stroke(), windowSize: 26 },
    indicators.ema12 && { yAccessor: ema12.accessor(), type: "EMA", stroke: ema12.stroke(), windowSize: 12 },
    indicators.sma   && { yAccessor: smaCalc.accessor(), type: "SMA", stroke: SMA_STROKE, windowSize: smaPeriod },
  ].filter(Boolean);

  // ── Unified hover tooltip content ─────────────────────────────────────────
  const hoverTooltipContent = ({ currentItem, xAccessor }) => {
    if (!currentItem) return { x: "", y: [] };
    const o = visibleOHLC(currentItem);
    const lines = [
      { label: "Open",  value: priceFormat(o.open) },
      { label: "High",  value: priceFormat(o.high) },
      { label: "Low",   value: priceFormat(o.low) },
      { label: "Close", value: priceFormat(o.close), stroke: openCloseColor(currentItem) },
    ];
    if (indicators.ema12 && Number.isFinite(currentItem.ema12))
      lines.push({ label: "EMA 12", value: priceFormat(currentItem.ema12), stroke: ema12.stroke() });
    if (indicators.ema26 && Number.isFinite(currentItem.ema26))
      lines.push({ label: "EMA 26", value: priceFormat(currentItem.ema26), stroke: ema26.stroke() });
    if (indicators.sma && Number.isFinite(currentItem.smaCustom))
      lines.push({ label: `SMA ${smaPeriod}`, value: priceFormat(currentItem.smaCustom), stroke: SMA_STROKE });
    if (indicators.vwap && Number.isFinite(currentItem.vwap))
      lines.push({ label: "VWAP", value: priceFormat(currentItem.vwap), stroke: VWAP_STROKE });
    if (indicators.bb && currentItem.bb)
      lines.push({
        label: "BB U/M/L",
        value: `${priceFormat(currentItem.bb.top)} / ${priceFormat(currentItem.bb.middle)} / ${priceFormat(currentItem.bb.bottom)}`,
        stroke: BB_APPEARANCE.stroke.middle,
      });
    if (indicators.rsi && Number.isFinite(currentItem.rsi))
      lines.push({ label: "RSI", value: priceFormat(currentItem.rsi) });
    if (indicators.macd && currentItem.macd)
      lines.push({
        label: "MACD",
        value: `${priceFormat(currentItem.macd.macd)} / sig ${priceFormat(currentItem.macd.signal)}`,
        stroke: MACD_APPEARANCE.strokeStyle.macd,
      });
    if (indicators.stoch && currentItem.stoch)
      lines.push({
        label: "Stoch %K/%D",
        value: `${priceFormat(currentItem.stoch.K)} / ${priceFormat(currentItem.stoch.D)}`,
      });
    if (indicators.atr && Number.isFinite(currentItem.atr))
      lines.push({ label: "ATR", value: priceFormat(currentItem.atr), stroke: ATR_STROKE });
    if (indicators.volume && Number.isFinite(currentItem.volume))
      lines.push({ label: "Vol", value: volumeFormat(currentItem.volume) });

    return { x: dateFormat(xAccessor(currentItem)), y: lines };
  };

  return (
    <div ref={containerRef} style={{ width: "100%", position: "relative" }}>

      {/* ── Header: timeframe tabs + candle-type group ──────────── */}
      <div style={headerStyles.bar}>
        <div style={headerStyles.group}>
          {TIMEFRAME_OPTIONS.map(({ key }) => (
            <button
              key={key}
              style={headerStyles.tab(timeframe === key)}
              onClick={() => setTimeframe(key)}
            >
              {key}
            </button>
          ))}
        </div>
        <div style={headerStyles.group}>
          {CANDLE_TYPES.map(({ key, label }) => (
            <button
              key={key}
              style={headerStyles.tab(candleType === key)}
              onClick={() => setCandleType(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Indicator toggle dropdown ───────────────────────────── */}
      <div ref={dropdownRef} style={dropdownStyles.wrapper}>
        <button
          style={dropdownStyles.button}
          onClick={() => setDropdownOpen((o) => !o)}
        >
          Indicators {dropdownOpen ? "▲" : "▼"}
        </button>
        {dropdownOpen && (
          <div style={dropdownStyles.panel}>
            {INDICATOR_OPTIONS.map(({ key, label }) => (
              <label key={key} style={dropdownStyles.row}>
                <input
                  type="checkbox"
                  style={dropdownStyles.checkbox}
                  checked={indicators[key]}
                  onChange={() => toggle(key)}
                />
                {label}
                {key === "sma" && (
                  <input
                    type="number"
                    min={SMA_MIN}
                    max={SMA_MAX}
                    value={smaPeriod}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => {
                      const v = parseInt(e.target.value, 10);
                      if (Number.isFinite(v)) {
                        setSmaPeriod(Math.max(SMA_MIN, Math.min(SMA_MAX, v)));
                      }
                    }}
                    style={dropdownStyles.periodInput}
                    aria-label="SMA period"
                  />
                )}
              </label>
            ))}
          </div>
        )}
      </div>

      {/* ── Chart ──────────────────────────────────────────────── */}
      <ChartWrapper yAxisTitle="Price (VND)" xAxisTitle="Date">
        <ChartCanvas
          height={totalHeight}
          ratio={window.devicePixelRatio || 1}
          width={chartWidth}
          margin={margin}
          data={data}
          displayXAccessor={displayXAccessor}
          seriesName="Data"
          xScale={xScale}
          xAccessor={xAccessor}
          xExtents={xExtents}
          zoomAnchor={lastVisibleItemBasedZoomAnchor}
        >
          {/* ── Price pane — left Y-axis (VND) ──────────────────── */}
          <Chart
            id={1}
            height={priceHeight}
            origin={[0, 0]}
            yExtents={(d) => {
              const o = visibleOHLC(d);
              const lows  = [o.low];
              const highs = [o.high];
              if (indicators.bb && d.bb) {
                lows.push(d.bb.bottom);
                highs.push(d.bb.top);
              }
              if (indicators.vwap && Number.isFinite(d.vwap)) {
                lows.push(d.vwap);
                highs.push(d.vwap);
              }
              return [Math.max(...highs), Math.min(...lows)];
            }}
          >
            <XAxis {...getXAxisProps({ showTickLabel: false })} />
            <YAxis tickFormat={priceFormat} {...getYAxisProps()} />
            {candleType === "ohlc" ? (
              <OHLCSeries yAccessor={visibleOHLC} stroke={openCloseColor} />
            ) : (
              <CandlestickSeries yAccessor={visibleOHLC} />
            )}
            {indicators.bb && (
              <BollingerSeries
                yAccessor={bbCalc.accessor()}
                strokeStyle={BB_APPEARANCE.stroke}
                fillStyle={BB_APPEARANCE.fill}
              />
            )}
            {indicators.ema26 && (
              <LineSeries yAccessor={ema26.accessor()} strokeStyle={ema26.stroke()} />
            )}
            {indicators.ema12 && (
              <LineSeries yAccessor={ema12.accessor()} strokeStyle={ema12.stroke()} />
            )}
            {indicators.sma && (
              <LineSeries yAccessor={smaCalc.accessor()} strokeStyle={SMA_STROKE} />
            )}
            {indicators.vwap && (
              <LineSeries yAccessor={(d) => d.vwap} strokeStyle={VWAP_STROKE} />
            )}
            {indicators.sar && (
              <SARSeries yAccessor={(d) => d.sar} />
            )}
            <MouseCoordinateY rectWidth={margin.right} displayFormat={priceFormat} />
            <EdgeIndicator
              itemType="last"
              rectWidth={margin.right}
              fill={openCloseColor}
              lineStroke={openCloseColor}
              displayFormat={priceFormat}
              yAccessor={(d) => d.close}
            />
            {maTooltipOptions.length > 0 && (
              <MovingAverageTooltip origin={[8, 24]} options={maTooltipOptions} />
            )}
            {indicators.bb && (
              <BollingerBandTooltip
                origin={[8, 40]}
                yAccessor={bbCalc.accessor()}
                options={bbCalc.options()}
                displayFormat={priceFormat}
              />
            )}
            <ZoomButtons />
            <OHLCTooltip origin={[8, 16]} />
            <HoverTooltip
              yAccessor={(d) => visibleOHLC(d).close}
              tooltip={{ content: hoverTooltipContent }}
              fontSize={11}
              fontFamily="Inter, sans-serif"
            />
          </Chart>

          {/* ── RSI overlay — right Y-axis (0–100) ──────────────── */}
          {indicators.rsi && (
            <Chart
              id={2}
              height={priceHeight}
              origin={[0, 0]}
              yExtents={[0, 100]}
            >
              <YAxis
                axisAt="right"
                orient="right"
                ticks={4}
                tickValues={[30, 50, 70]}
                tickFormat={(v) => v}
                {...getYAxisProps({ showGridLines: false })}
              />
              <RSISeries
                yAccessor={rsiCalc.accessor()}
                overSold={30}
                middle={50}
                overBought={70}
              />
              <RSITooltip
                origin={[8, 48]}
                yAccessor={rsiCalc.accessor()}
                options={rsiCalc.options()}
                displayFormat={priceFormat}
              />
            </Chart>
          )}

          {/* ── MACD pane ────────────────────────────────────────── */}
          {indicators.macd && (
            <Chart
              id={3}
              height={SUB_PANE_HEIGHTS.macd}
              origin={[0, paneOrigin.macd]}
              yExtents={macdCalc.accessor()}
              padding={{ top: 8, bottom: 8 }}
            >
              <XAxis {...getXAxisProps({ showTickLabel: isBottomSubPane("macd") })} />
              <YAxis ticks={3} tickFormat={priceFormat} {...getYAxisProps()} />
              <MACDSeries
                yAccessor={macdCalc.accessor()}
                strokeStyle={MACD_APPEARANCE.strokeStyle}
                fillStyle={MACD_APPEARANCE.fillStyle}
              />
              <MACDTooltip
                origin={[8, 16]}
                yAccessor={macdCalc.accessor()}
                options={macdCalc.options()}
                appearance={MACD_APPEARANCE}
                displayFormat={priceFormat}
              />
              {isBottomSubPane("macd") && (
                <MouseCoordinateX displayFormat={dateFormat} />
              )}
              <MouseCoordinateY rectWidth={margin.right} displayFormat={priceFormat} />
            </Chart>
          )}

          {/* ── Stochastic Oscillator pane ───────────────────────── */}
          {indicators.stoch && (
            <Chart
              id={5}
              height={SUB_PANE_HEIGHTS.stoch}
              origin={[0, paneOrigin.stoch]}
              yExtents={[0, 100]}
              padding={{ top: 8, bottom: 8 }}
            >
              <XAxis {...getXAxisProps({ showTickLabel: isBottomSubPane("stoch") })} />
              <YAxis
                ticks={2}
                tickValues={[20, 80]}
                tickFormat={(v) => v}
                {...getYAxisProps()}
              />
              <StochasticSeries
                yAccessor={stochCalc.accessor()}
                overSold={20}
                middle={50}
                overBought={80}
              />
              <StochasticTooltip
                origin={[8, 16]}
                yAccessor={stochCalc.accessor()}
                options={stochCalc.options()}
                appearance={StochasticSeries.defaultProps}
                label="Stoch"
              />
              {isBottomSubPane("stoch") && (
                <MouseCoordinateX displayFormat={dateFormat} />
              )}
              <MouseCoordinateY rectWidth={margin.right} displayFormat={priceFormat} />
            </Chart>
          )}

          {/* ── ATR pane ─────────────────────────────────────────── */}
          {indicators.atr && (
            <Chart
              id={6}
              height={SUB_PANE_HEIGHTS.atr}
              origin={[0, paneOrigin.atr]}
              yExtents={atrCalc.accessor()}
              padding={{ top: 8, bottom: 8 }}
            >
              <XAxis {...getXAxisProps({ showTickLabel: isBottomSubPane("atr") })} />
              <YAxis ticks={2} tickFormat={priceFormat} {...getYAxisProps()} />
              <LineSeries yAccessor={atrCalc.accessor()} strokeStyle={ATR_STROKE} />
              <SingleValueTooltip
                origin={[8, 16]}
                yAccessor={atrCalc.accessor()}
                yLabel="ATR (14)"
                yDisplayFormat={priceFormat}
              />
              {isBottomSubPane("atr") && (
                <MouseCoordinateX displayFormat={dateFormat} />
              )}
              <MouseCoordinateY rectWidth={margin.right} displayFormat={priceFormat} />
            </Chart>
          )}

          {/* ── Volume pane (bottom) ─────────────────────────────── */}
          {indicators.volume && (
            <Chart
              id={4}
              height={SUB_PANE_HEIGHTS.volume}
              origin={[0, paneOrigin.volume]}
              yExtents={(d) => d.volume}
            >
              <XAxis {...getXAxisProps({ showTickLabel: isBottomSubPane("volume") })} />
              <YAxis ticks={2} tickFormat={volumeFormat} {...getYAxisProps()} />
              <BarSeries fillStyle={volumeColor} yAccessor={(d) => d.volume} />
              {isBottomSubPane("volume") && (
                <MouseCoordinateX displayFormat={dateFormat} />
              )}
              <MouseCoordinateY rectWidth={margin.right} displayFormat={volumeFormat} />
            </Chart>
          )}

          <CrossHairCursor />
        </ChartCanvas>
      </ChartWrapper>
    </div>
  );
}
