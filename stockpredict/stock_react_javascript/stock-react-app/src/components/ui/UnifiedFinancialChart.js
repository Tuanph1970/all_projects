import React, { useState } from 'react';
import { format } from "d3-format";
import { timeFormat } from "d3-time-format";
import {
  discontinuousTimeScaleProviderBuilder,
  Chart,
  ChartCanvas,
  LineSeries,
  BarSeries,
  XAxis,
  YAxis,
  CrossHairCursor,
  EdgeIndicator,
  MouseCoordinateX,
  MouseCoordinateY,
  ZoomButtons,
  SingleValueTooltip,
  lastVisibleItemBasedZoomAnchor
} from "react-financial-charts";
import { getXAxisProps, getYAxisProps } from '../../constants/chartTheme';
import ChartWrapper from './ChartWrapper';

// ── Unified single-panel financial chart ────────────────────────────────────
// One chart "content": price-scale series on the LEFT y-axis, indicators on the
// RIGHT y-axis (overlaid on the same pane), and volume drawn INVERTED below the
// date axis. A "Series" dropdown of checkboxes toggles each line. Only volume is
// a bar series; everything else is a smooth line. Shared by the Solution modal
// (Training/Prediction) and AI Insights so all technical charts look the same.
//
// The component renders whatever series are actually present in `data` (it probes
// each field), so producers only need to supply the canonical snake_case field
// names below; absent series are silently skipped.

// Price-scale series (left axis).
const PRICE_SERIES = [
  { key: 'close',      label: 'Close',      color: '#111827', field: 'close',      width: 1.5 },
  { key: 'actual',     label: 'Actual',     color: '#2196F3', field: 'actual',     width: 2 },
  { key: 'predicted',  label: 'Predicted',  color: '#4CAF50', field: 'predicted',  width: 2, dash: '5,5' },
  { key: 'validation', label: 'Validation', color: '#FF9800', field: 'validation', width: 2, dash: '3,3' },
  { key: 'sma_20',     label: 'SMA 20',     color: '#2563eb', field: 'sma_20',     width: 1.5 },
  { key: 'sma_50',     label: 'SMA 50',     color: '#f59e0b', field: 'sma_50',     width: 1.5 },
  { key: 'ema_12',     label: 'EMA 12',     color: '#10b981', field: 'ema_12',     width: 1.5 },
  { key: 'wma',        label: 'WMA',        color: '#0891b2', field: 'wma',        width: 1.5 },
  { key: 'dema',       label: 'DEMA',       color: '#e11d48', field: 'dema',       width: 1.5 },
  { key: 'tema',       label: 'TEMA',       color: '#7c3aed', field: 'tema',       width: 1.5 },
  { key: 'vwap',       label: 'VWAP',       color: '#14b8a6', field: 'vwap',       width: 1.5 },
  { key: 'psar',       label: 'PSAR',       color: '#d97706', field: 'psar',       width: 1, dash: '2,2' },
];

// Bollinger band rendered as one toggle (3 lines).
const BB_SERIES = { key: 'bb', label: 'Bollinger Bands', color: '#8b5cf6', field: 'bb_upper' };

// Indicators that share the RIGHT y-axis.
const OSC_SERIES = [
  { key: 'rsi',   label: 'RSI',        color: '#9c27b0', field: 'rsi' },
  { key: 'macd',  label: 'MACD',       color: '#2196F3', field: 'macd' },
  { key: 'cci',   label: 'CCI',        color: '#0ea5e9', field: 'cci' },
  { key: 'stoch', label: 'Stochastic', color: '#f43f5e', field: 'stoch_k' },
  { key: 'mfi',   label: 'MFI',        color: '#f97316', field: 'mfi' },
  { key: 'adx',   label: 'ADX',        color: '#22c55e', field: 'adx' },
  { key: 'atr',   label: 'ATR',        color: '#ec4899', field: 'atr' },
];

const toChartDate = (item, index, len) => {
  if (item.date instanceof Date) return item.date;
  if (typeof item.date === 'string') {
    let d = new Date(item.date);
    if (isNaN(d.getTime())) {
      const p = item.date.split('-');
      if (p.length === 3) d = new Date(parseInt(p[0]), parseInt(p[1]) - 1, parseInt(p[2]));
    }
    return d;
  }
  const d = new Date();
  d.setDate(d.getDate() - (len - index));
  return d;
};

const UnifiedFinancialChart = ({ data, ticker }) => {
  // Price overlays default on; oscillators default off (they share a single
  // right axis, so turning them all on at once would be unreadable). Volume on.
  const [visible, setVisible] = useState(() => {
    const v = { close: true, actual: true, predicted: true, validation: true, bb: true, volume: true };
    PRICE_SERIES.forEach(s => { if (!(s.key in v)) v[s.key] = true; });
    OSC_SERIES.forEach(s => { v[s.key] = false; });
    return v;
  });
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const srcLen = (data || []).length;
  const chartData = (data || [])
    .map((item, index) => ({ ...item, date: toChartDate(item, index, srcLen) }))
    .filter(d => d.date && !isNaN(d.date.getTime()));

  if (chartData.length === 0) {
    return <div className="text-center text-muted py-5">No chart data available</div>;
  }

  const has = (field) => chartData.some(d => d[field] !== undefined && d[field] !== null && !isNaN(d[field]));
  const availPrice = PRICE_SERIES.filter(s => has(s.field));
  const availBB = has('bb_upper') && has('bb_lower');
  const availOsc = OSC_SERIES.filter(s => has(s.field));
  const hasVolume = chartData.some(d => Number.isFinite(d.volume) && d.volume > 0);

  const shownPrice = availPrice.filter(s => visible[s.key]);
  const shownOsc = availOsc.filter(s => visible[s.key]);
  const showVolume = hasVolume && visible.volume;

  const availableKeys = [
    ...availPrice.map(s => s.key),
    ...(availBB ? ['bb'] : []),
    ...availOsc.map(s => s.key),
    ...(hasVolume ? ['volume'] : []),
  ];
  const activeCount = availableKeys.filter(k => visible[k]).length;

  const ScaleProvider = discontinuousTimeScaleProviderBuilder().inputDateAccessor(d => d.date);
  const { data: scaledData, xScale, xAccessor, displayXAccessor } = ScaleProvider(chartData);

  const priceFormat = format('.2f');
  const volumeFormat = format('.2s');
  const timeDisplayFormat = timeFormat('%d %b');

  const max = xAccessor(scaledData[scaledData.length - 1]);
  const min = xAccessor(scaledData[Math.max(0, scaledData.length - 120)]);
  const xExtents = [min, max + 5];

  const width = 1100;
  const margin = { left: 60, right: 70, top: 16, bottom: 30 };
  const mainHeight = 420;
  const volumeHeight = showVolume ? 90 : 0;
  const totalHeight = mainHeight + volumeHeight + 16;

  const volumeColor = d => (d.close || d.actual || 0) >= (d.open || d.close || d.actual || 0)
    ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)';
  const edgeColor = d => (d.close || d.actual || 0) >= (d.open || d.close || d.actual || 0) ? '#26a69a' : '#ef5350';

  // Left-axis extents over every visible price-scale series (+ Bollinger).
  const priceFields = shownPrice.map(s => s.field);
  const priceYExtents = d => {
    const vals = [];
    priceFields.forEach(f => { if (Number.isFinite(d[f])) vals.push(d[f]); });
    if (visible.bb && availBB) {
      if (Number.isFinite(d.bb_upper)) vals.push(d.bb_upper);
      if (Number.isFinite(d.bb_lower)) vals.push(d.bb_lower);
    }
    if (vals.length === 0) return [0, 1];
    return [Math.min(...vals) * 0.99, Math.max(...vals) * 1.01];
  };

  // Right-axis extents over every visible indicator series.
  const oscFields = [];
  shownOsc.forEach(s => {
    oscFields.push(s.field);
    if (s.key === 'macd') oscFields.push('macd_signal');
    if (s.key === 'stoch') oscFields.push('stoch_d');
  });
  const oscYExtents = d => {
    const vals = [];
    oscFields.forEach(f => { if (Number.isFinite(d[f])) vals.push(d[f]); });
    if (vals.length === 0) return [0, 100];
    const lo = Math.min(...vals), hi = Math.max(...vals);
    return lo === hi ? [lo - 1, hi + 1] : [lo, hi];
  };

  const groups = [
    { title: 'Price (left axis)', items: [...availPrice, ...(availBB ? [BB_SERIES] : [])] },
    { title: 'Indicators (right axis)', items: availOsc },
    ...(hasVolume ? [{ title: 'Volume', items: [{ key: 'volume', label: 'Volume', color: '#64748b' }] }] : []),
  ].filter(g => g.items.length > 0);

  return (
    <div>
      {/* Series toggle dropdown */}
      <div className="d-flex justify-content-end mb-2" style={{ position: 'relative' }}>
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-2"
          onClick={() => setDropdownOpen(o => !o)}
        >
          <span>Series</span>
          <span className="badge bg-primary">{activeCount}</span>
          <span style={{ fontSize: '0.7rem' }}>{dropdownOpen ? '▲' : '▼'}</span>
        </button>
        {dropdownOpen && (
          <>
            <div style={{ position: 'fixed', inset: 0, zIndex: 1040 }} onClick={() => setDropdownOpen(false)} />
            <div
              style={{
                position: 'absolute', right: 0, top: '100%', marginTop: 4, zIndex: 1050,
                background: '#fff', border: '1px solid #dee2e6', borderRadius: 8,
                boxShadow: '0 6px 18px rgba(0,0,0,0.12)', minWidth: 230, padding: 8,
                maxHeight: 360, overflowY: 'auto',
              }}
            >
              {groups.map(g => (
                <div key={g.title} className="mb-1">
                  <div className="text-muted text-uppercase fw-semibold px-2 py-1" style={{ fontSize: '0.7rem' }}>{g.title}</div>
                  {g.items.map(s => (
                    <label
                      key={s.key}
                      className="d-flex align-items-center gap-2 px-2 py-1 rounded"
                      style={{ cursor: 'pointer', fontSize: '0.85rem' }}
                    >
                      <input
                        type="checkbox"
                        checked={!!visible[s.key]}
                        onChange={() => setVisible(p => ({ ...p, [s.key]: !p[s.key] }))}
                      />
                      <span style={{ width: 10, height: 10, borderRadius: '50%', background: s.color, display: 'inline-block' }} />
                      <span>{s.label}</span>
                    </label>
                  ))}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <div style={{ overflow: 'auto' }}>
        <ChartWrapper yAxisTitle="Price (VND)" xAxisTitle="Date">
          <ChartCanvas
            height={totalHeight}
            ratio={2}
            width={width}
            margin={margin}
            data={scaledData}
            displayXAccessor={displayXAccessor}
            seriesName={ticker || 'Series'}
            xScale={xScale}
            xAccessor={xAccessor}
            xExtents={xExtents}
            zoomAnchor={lastVisibleItemBasedZoomAnchor}
          >
            {/* Price pane — left Y-axis */}
            <Chart id={1} height={mainHeight} origin={[0, 0]} yExtents={priceYExtents}>
              <XAxis showGridLines {...getXAxisProps()} />
              <YAxis showGridLines axisAt="left" orient="left" tickFormat={priceFormat} {...getYAxisProps()} />

              {visible.bb && availBB && (
                <>
                  <LineSeries yAccessor={d => d.bb_upper} strokeStyle="#8b5cf6" strokeWidth={1} strokeDasharray="3,3" />
                  <LineSeries yAccessor={d => d.bb_middle} strokeStyle="#a78bfa" strokeWidth={1} />
                  <LineSeries yAccessor={d => d.bb_lower} strokeStyle="#8b5cf6" strokeWidth={1} strokeDasharray="3,3" />
                </>
              )}
              {shownPrice.map(s => (
                <LineSeries
                  key={s.key}
                  yAccessor={d => d[s.field]}
                  strokeStyle={s.color}
                  strokeWidth={s.width}
                  strokeDasharray={s.dash ? s.dash : undefined}
                />
              ))}

              <MouseCoordinateY rectWidth={margin.right} displayFormat={priceFormat} />
              <EdgeIndicator
                itemType="last"
                rectWidth={margin.right}
                fill={edgeColor}
                lineStroke={edgeColor}
                displayFormat={priceFormat}
                yAccessor={d => (Number.isFinite(d.close) ? d.close : d.actual)}
              />
              {shownPrice.slice(0, 4).map((s, i) => (
                <SingleValueTooltip
                  key={s.key}
                  yAccessor={d => d[s.field]}
                  yLabel={s.label}
                  yDisplayFormat={priceFormat}
                  origin={[8 + i * 110, 16]}
                  labelFill={s.color}
                />
              ))}
              <ZoomButtons />
              <MouseCoordinateX displayFormat={timeDisplayFormat} />
            </Chart>

            {/* Indicators — right Y-axis, overlaid on the price pane */}
            {shownOsc.length > 0 && (
              <Chart id={2} height={mainHeight} origin={[0, 0]} yExtents={oscYExtents}>
                <YAxis axisAt="right" orient="right" tickFormat={d => priceFormat(d)} {...getYAxisProps()} showGridLines={false} />
                {shownOsc.map((s, i) => (
                  <React.Fragment key={s.key}>
                    <LineSeries yAccessor={d => d[s.field]} strokeStyle={s.color} strokeWidth={1.5} />
                    {s.key === 'macd' && <LineSeries yAccessor={d => d.macd_signal} strokeStyle="#FF9800" strokeWidth={1.5} />}
                    {s.key === 'stoch' && <LineSeries yAccessor={d => d.stoch_d} strokeStyle="#FF9800" strokeWidth={1.5} />}
                    <SingleValueTooltip
                      yAccessor={d => d[s.field]}
                      yLabel={s.label}
                      yDisplayFormat={priceFormat}
                      origin={[8 + i * 90, 36]}
                      labelFill={s.color}
                    />
                  </React.Fragment>
                ))}
              </Chart>
            )}

            {/* Volume — inverted bars drawn below the date axis */}
            {showVolume && (
              <Chart id={3} height={volumeHeight} origin={[0, mainHeight]} yExtents={d => [0, d.volume]} flipYScale>
                <YAxis axisAt="left" orient="left" ticks={2} tickFormat={volumeFormat} {...getYAxisProps()} showGridLines={false} />
                <BarSeries fillStyle={volumeColor} yAccessor={d => d.volume} />
                <SingleValueTooltip yAccessor={d => d.volume} yLabel="Volume" yDisplayFormat={volumeFormat} origin={[8, 14]} />
                <MouseCoordinateY rectWidth={margin.right} displayFormat={volumeFormat} />
              </Chart>
            )}

            <CrossHairCursor />
          </ChartCanvas>
        </ChartWrapper>
      </div>
      <div className="mt-2 text-muted" style={{ fontSize: '0.75rem' }}>
        Tip: use the <strong>Series</strong> menu to toggle lines. Left axis = price, right axis = indicators, volume below the date axis. Scroll to zoom, drag to pan.
      </div>
    </div>
  );
};

export default UnifiedFinancialChart;
