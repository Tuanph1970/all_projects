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
// One chart "content": price-scale series on the LEFT y-axis, non-price
// indicators on the RIGHT y-axis (overlaid on the same pane), and volume drawn
// INVERTED below the date axis. A "Series" dropdown of checkboxes toggles each
// line on/off. Only volume is a bar series; everything else is a smooth line.
// Shared by the Solution modal (Training/Prediction) and AI Insights.
//
// The component renders whatever series are actually present in `data` (it
// probes each field), so producers only need to supply the canonical snake_case
// field names below; absent series are silently skipped. That means the chart
// shows exactly the indicators the solution selected — each as its own checkbox.

// Price-scale single-line series (LEFT axis).
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

// Multi-line price-scale overlays (LEFT axis). One checkbox toggles the group.
// `color` is the legend swatch; each line carries its own color/dash.
const PRICE_BANDS = [
  { key: 'bb', label: 'Bollinger Bands', color: '#8b5cf6', lines: [
    { field: 'bb_upper',  color: '#8b5cf6', dash: '3,3' },
    { field: 'bb_middle', color: '#a78bfa' },
    { field: 'bb_lower',  color: '#8b5cf6', dash: '3,3' },
  ] },
  { key: 'ichimoku', label: 'Ichimoku Cloud', color: '#2563eb', lines: [
    { field: 'ichimoku_conv', color: '#2563eb' },
    { field: 'ichimoku_base', color: '#dc2626' },
    { field: 'ichimoku_a',    color: '#16a34a', dash: '4,2' },
    { field: 'ichimoku_b',    color: '#9333ea', dash: '4,2' },
  ] },
  { key: 'keltner', label: 'Keltner Channel', color: '#0891b2', lines: [
    { field: 'kc_upper',  color: '#0891b2', dash: '3,3' },
    { field: 'kc_middle', color: '#22d3ee' },
    { field: 'kc_lower',  color: '#0891b2', dash: '3,3' },
  ] },
  { key: 'donchian', label: 'Donchian Channel', color: '#ca8a04', lines: [
    { field: 'dc_upper',  color: '#ca8a04', dash: '3,3' },
    { field: 'dc_middle', color: '#eab308' },
    { field: 'dc_lower',  color: '#ca8a04', dash: '3,3' },
  ] },
];

// Non-price indicators that share the RIGHT y-axis (auto-scaled to whatever is
// visible — so an oscillator like RSI reads 0-100 and Momentum reads its own
// range, independent of price). `extra` lists additional lines in the group.
const OSC_SERIES = [
  { key: 'rsi',        label: 'RSI',          color: '#9c27b0', field: 'rsi' },
  { key: 'macd',       label: 'MACD',         color: '#2196F3', field: 'macd',        extra: [{ field: 'macd_signal', color: '#FF9800' }] },
  { key: 'cci',        label: 'CCI',          color: '#0ea5e9', field: 'cci' },
  { key: 'stoch',      label: 'Stochastic',   color: '#f43f5e', field: 'stoch_k',     extra: [{ field: 'stoch_d', color: '#FF9800' }] },
  { key: 'stoch_rsi',  label: 'Stoch RSI',    color: '#db2777', field: 'stoch_rsi_k', extra: [{ field: 'stoch_rsi_d', color: '#fb923c' }] },
  { key: 'mfi',        label: 'MFI',          color: '#f97316', field: 'mfi' },
  { key: 'adx',        label: 'ADX',          color: '#22c55e', field: 'adx' },
  { key: 'atr',        label: 'ATR',          color: '#ec4899', field: 'atr' },
  { key: 'mom',        label: 'Momentum',     color: '#6366f1', field: 'mom' },
  { key: 'supertrend', label: 'Schaff Trend (STC)', color: '#0d9488', field: 'supertrend' },
  { key: 'roc',        label: 'ROC',          color: '#0d9488', field: 'roc' },
  { key: 'williams_r', label: 'Williams %R',  color: '#a855f7', field: 'williams_r' },
  { key: 'tsi',        label: 'TSI',          color: '#0369a1', field: 'tsi' },
  { key: 'uo',         label: 'Ultimate Osc', color: '#d97706', field: 'uo' },
  { key: 'ao',         label: 'Awesome Osc',  color: '#16a34a', field: 'ao' },
  { key: 'aroon',      label: 'Aroon',        color: '#16a34a', field: 'aroon_up',    extra: [{ field: 'aroon_down', color: '#dc2626' }] },
  { key: 'vortex',     label: 'Vortex',       color: '#2563eb', field: 'vortex_pos',  extra: [{ field: 'vortex_neg', color: '#dc2626' }] },
  { key: 'stddev',     label: 'Std Dev',      color: '#64748b', field: 'stddev' },
  { key: 'hv',         label: 'Hist. Vol',    color: '#9333ea', field: 'hv' },
  { key: 'cmf',        label: 'CMF',          color: '#0d9488', field: 'cmf' },
  { key: 'cho',        label: 'Chaikin Osc',  color: '#e11d48', field: 'cho' },
  { key: 'eom',        label: 'Ease of Move', color: '#7c3aed', field: 'eom' },
  { key: 'fi',         label: 'Force Index',  color: '#b45309', field: 'fi' },
  { key: 'nvi',        label: 'NVI',          color: '#0891b2', field: 'nvi' },
  { key: 'pvi',        label: 'PVI',          color: '#65a30d', field: 'pvi' },
  { key: 'vosc',       label: 'Volume Osc',   color: '#db2777', field: 'vosc' },
  { key: 'volume_ma',  label: 'Volume MA',    color: '#94a3b8', field: 'volume_ma' },
  { key: 'obv',        label: 'OBV',          color: '#0369a1', field: 'obv' },
  { key: 'ad',         label: 'Accum/Dist',   color: '#475569', field: 'ad' },
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
  // right axis, so turning them all on at once would be unreadable — toggle the
  // ones you want from the Series menu). Volume on.
  const [visible, setVisible] = useState(() => {
    const v = { close: true, actual: true, predicted: true, validation: true, volume: true };
    PRICE_SERIES.forEach(s => { if (!(s.key in v)) v[s.key] = true; });
    PRICE_BANDS.forEach(b => { v[b.key] = true; });
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
  const availBands = PRICE_BANDS.filter(b => b.lines.some(ln => has(ln.field)));
  const availOsc = OSC_SERIES.filter(s => has(s.field));
  const hasVolume = chartData.some(d => Number.isFinite(d.volume) && d.volume > 0);

  const shownPrice = availPrice.filter(s => visible[s.key]);
  const shownBands = availBands.filter(b => visible[b.key]);
  const shownOsc = availOsc.filter(s => visible[s.key]);
  const showVolume = hasVolume && visible.volume;

  const availableKeys = [
    ...availPrice.map(s => s.key),
    ...availBands.map(b => b.key),
    ...availOsc.map(s => s.key),
    ...(hasVolume ? ['volume'] : []),
  ];
  const activeCount = availableKeys.filter(k => visible[k]).length;

  const ScaleProvider = discontinuousTimeScaleProviderBuilder().inputDateAccessor(d => d.date);
  const { data: scaledData, xScale, xAccessor, displayXAccessor } = ScaleProvider(chartData);

  const priceFormat = format('.2f');
  // Right axis hosts indicators of wildly different scale (RSI ~0-100, Momentum
  // ~±4, AD/OBV in the millions). Use compact SI for large magnitudes and plain
  // decimals for small ones so neither reads awkwardly.
  const siFormat = format('.2s');
  const oscFormat = (v) => (Math.abs(v) >= 10000 ? siFormat(v) : format('.2f')(v));
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

  // Left-axis extents over every visible price-scale series (singles + bands).
  const priceYExtents = d => {
    const vals = [];
    shownPrice.forEach(s => { if (Number.isFinite(d[s.field])) vals.push(d[s.field]); });
    shownBands.forEach(b => b.lines.forEach(ln => { if (Number.isFinite(d[ln.field])) vals.push(d[ln.field]); }));
    if (vals.length === 0) return [0, 1];
    return [Math.min(...vals) * 0.99, Math.max(...vals) * 1.01];
  };

  // Right-axis extents over every visible indicator line (incl. extra lines).
  const oscFields = [];
  shownOsc.forEach(s => {
    oscFields.push(s.field);
    (s.extra || []).forEach(e => oscFields.push(e.field));
  });
  const oscYExtents = d => {
    const vals = [];
    oscFields.forEach(f => { if (Number.isFinite(d[f])) vals.push(d[f]); });
    if (vals.length === 0) return [0, 100];
    const lo = Math.min(...vals), hi = Math.max(...vals);
    return lo === hi ? [lo - 1, hi + 1] : [lo, hi];
  };

  const groups = [
    { title: 'Price (left axis)', items: [...availPrice, ...availBands.map(b => ({ key: b.key, label: b.label, color: b.color }))] },
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

              {shownBands.map(b => (
                <React.Fragment key={b.key}>
                  {b.lines.filter(ln => has(ln.field)).map(ln => (
                    <LineSeries
                      key={ln.field}
                      yAccessor={d => d[ln.field]}
                      strokeStyle={ln.color}
                      strokeWidth={1}
                      strokeDasharray={ln.dash ? ln.dash : undefined}
                    />
                  ))}
                </React.Fragment>
              ))}
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
                <YAxis axisAt="right" orient="right" tickFormat={oscFormat} {...getYAxisProps()} showGridLines={false} />
                {shownOsc.map((s, i) => (
                  <React.Fragment key={s.key}>
                    <LineSeries yAccessor={d => d[s.field]} strokeStyle={s.color} strokeWidth={1.5} />
                    {(s.extra || []).map(e => (
                      <LineSeries key={e.field} yAccessor={d => d[e.field]} strokeStyle={e.color} strokeWidth={1.5} />
                    ))}
                    <SingleValueTooltip
                      yAccessor={d => d[s.field]}
                      yLabel={s.label}
                      yDisplayFormat={oscFormat}
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
        Tip: use the <strong>Series</strong> menu to toggle lines. Left axis = price &amp; price overlays,
        right axis = indicators (auto-scaled, independent of price), volume below the date axis. Scroll to zoom, drag to pan.
      </div>
    </div>
  );
};

export default UnifiedFinancialChart;
