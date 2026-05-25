
import React, { useRef, useEffect, useState } from "react";
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
  discontinuousTimeScaleProviderBuilder,
  Chart,
  ChartCanvas,
  BarSeries,
  CandlestickSeries,
  SARSeries,
  LineSeries,
  RSISeries,
  MACDSeries,
  BollingerSeries,
  MovingAverageTooltip,
  OHLCTooltip,
  RSITooltip,
  MACDTooltip,
  BollingerBandTooltip,
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

const SMA_MIN = 2;
const SMA_MAX = 200;

const INDICATOR_OPTIONS = [
  { key: "ema12",  label: "EMA 12" },
  { key: "ema26",  label: "EMA 26" },
  { key: "sar",    label: "Parabolic SAR" },
  { key: "rsi",    label: "RSI (14)" },
  { key: "macd",   label: "MACD (12,26,9)" },
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

// ─────────────────────────────────────────────────────────────────────────────

export default function StockChart({ initialData }) {
  const containerRef   = useRef(null);
  const dropdownRef    = useRef(null);
  const [chartWidth,   setChartWidth]   = useState(900);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [indicators,   setIndicators]   = useState({
    ema12:  true,
    ema26:  true,
    sar:    true,
    rsi:    true,
    macd:   true,
    bb:     false,
    vwap:   false,
    sma:    false,
    volume: true,
  });
  const [smaPeriod, setSmaPeriod] = useState(20);

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
  const macdHeight  = indicators.macd   ? 100 : 0;
  const volHeight   = indicators.volume ? 80  : 0;
  const totalHeight = priceHeight + macdHeight + volHeight + margin.top + margin.bottom;

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

  const calculatedData = smaCalc(
    bbCalc(macdCalc(rsiCalc(defaultSar(ema26(ema12(initialData))))))
  );

  // VWAP — anchored cumulative from start of dataset (typical price * volume)
  let cumPV = 0;
  let cumV  = 0;
  for (const row of calculatedData) {
    const tp  = (row.high + row.low + row.close) / 3;
    const vol = row.volume || 0;
    cumPV += tp * vol;
    cumV  += vol;
    row.vwap = cumV > 0 ? cumPV / cumV : tp;
  }

  const { data, xScale, xAccessor, displayXAccessor } = ScaleProvider(calculatedData);

  const priceFormat  = format(".2f");
  const volumeFormat = format(".2s");
  const dateFormat   = timeFormat("%d %b");

  const max = xAccessor(data[data.length - 1]);
  const min = xAccessor(data[Math.max(0, data.length - 100)]);
  const xExtents = [min, max + 5];

  const volumeColor    = (d) => d.close > d.open ? chartColors.greenVolume  : chartColors.redVolume;
  const openCloseColor = (d) => d.close > d.open ? chartColors.greenCandle  : chartColors.redCandle;

  // tooltip entries depend on which moving averages are active
  const maTooltipOptions = [
    indicators.ema26 && { yAccessor: ema26.accessor(), type: "EMA", stroke: ema26.stroke(), windowSize: 26 },
    indicators.ema12 && { yAccessor: ema12.accessor(), type: "EMA", stroke: ema12.stroke(), windowSize: 12 },
    indicators.sma   && { yAccessor: smaCalc.accessor(), type: "SMA", stroke: SMA_STROKE, windowSize: smaPeriod },
  ].filter(Boolean);

  return (
    <div ref={containerRef} style={{ width: "100%", position: "relative" }}>

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
              const lows  = [d.low];
              const highs = [d.high];
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
            <CandlestickSeries />
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
              height={macdHeight}
              origin={[0, priceHeight]}
              yExtents={macdCalc.accessor()}
              padding={{ top: 8, bottom: 8 }}
            >
              <XAxis {...getXAxisProps({ showTickLabel: false })} />
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
              <MouseCoordinateY rectWidth={margin.right} displayFormat={priceFormat} />
            </Chart>
          )}

          {/* ── Volume pane (bottom) ─────────────────────────────── */}
          {indicators.volume && (
            <Chart
              id={4}
              height={volHeight}
              origin={[0, priceHeight + macdHeight]}
              yExtents={(d) => d.volume}
            >
              <XAxis {...getXAxisProps()} />
              <YAxis ticks={2} tickFormat={volumeFormat} {...getYAxisProps()} />
              <BarSeries fillStyle={volumeColor} yAccessor={(d) => d.volume} />
              <MouseCoordinateX displayFormat={dateFormat} />
              <MouseCoordinateY rectWidth={margin.right} displayFormat={volumeFormat} />
            </Chart>
          )}

          <CrossHairCursor />
        </ChartCanvas>
      </ChartWrapper>
    </div>
  );
}
