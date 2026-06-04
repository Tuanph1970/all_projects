// CD-4 — Volatility Forecast & Backtest UI
// HAR vs VMD-HAR comparison with Diebold-Mariano test +
// vol-targeting backtest with full equity-curve and drawdown analysis.
import React, { useState, useCallback } from 'react';
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine, ComposedChart, Bar,
} from 'recharts';
import {
  TrendingUp, RefreshCw, Zap, BarChart2, Award,
  AlertTriangle, CheckCircle, ChevronDown, ChevronUp, Activity,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import chartDecompService from '../../../services/chartDecompService';
import companyService from '../../../services/companyService';

// ── Palette ───────────────────────────────────────────────────────────────────

const C = {
  accent:  '#6366f1',
  accentL: '#eef2ff',
  success: '#10b981',
  warn:    '#f59e0b',
  danger:  '#ef4444',
  sky:     '#0ea5e9',
  purple:  '#8b5cf6',
  gray:    '#6b7280',
  border:  '#e5e7eb',
  bg:      '#f9fafb',
  card:    '#ffffff',
  dark:    '#111827',
  mid:     '#374151',
  light:   '#9ca3af',
};

const FONT = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";

// ── Base styles ───────────────────────────────────────────────────────────────

const s = {
  page: { background: C.bg, minHeight: '100vh', padding: '20px 24px', fontFamily: FONT },
  card: { background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, padding: '16px 20px', marginBottom: 16 },
  cardSm: { background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: '12px 16px' },
  sectionTitle: { fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: C.mid, marginBottom: 12 },
  row: { display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' },
  field: { display: 'flex', flexDirection: 'column', gap: 4 },
  label: { fontSize: 11, fontWeight: 600, color: C.gray, textTransform: 'uppercase', letterSpacing: '0.05em' },
  input: { height: 36, border: `1px solid ${C.border}`, borderRadius: 8, padding: '0 10px', fontSize: 13, fontFamily: FONT, color: C.dark, outline: 'none', background: '#fff', minWidth: 90 },
  select: { height: 36, border: `1px solid ${C.border}`, borderRadius: 8, padding: '0 8px', fontSize: 13, fontFamily: FONT, color: C.dark, background: '#fff', cursor: 'pointer' },
  btn: (bg = C.accent, light = false) => ({
    height: 36, padding: '0 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
    fontSize: 13, fontWeight: 600, fontFamily: FONT,
    background: light ? C.accentL : bg, color: light ? C.accent : '#fff',
    display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
  }),
  error: { background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', fontSize: 13, color: '#b91c1c', marginTop: 10 },
  info:  { background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: '10px 14px', fontSize: 13, color: '#166534', marginTop: 10 },
  badge: (color = C.gray, bg = '#f3f4f6') => ({
    display: 'inline-flex', alignItems: 'center', gap: 4,
    padding: '3px 10px', borderRadius: 99, fontSize: 11, fontWeight: 700, color, background: bg,
  }),
  metricBox: { flex: 1, minWidth: 110, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '12px 14px' },
  chartTitle: { fontSize: 12, fontWeight: 700, color: C.mid, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' },
  divider: { height: 1, background: C.border, margin: '12px 0' },
  configGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 },
  th: { background: C.bg, padding: '8px 12px', textAlign: 'left', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em', color: C.gray, borderBottom: `1px solid ${C.border}` },
  td: { padding: '9px 12px', fontSize: 13, color: C.mid, borderBottom: `1px solid #f3f4f6` },
};

const Spin = () => <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />;
const MetricCard = ({ label, value, color, sub }) => (
  <div style={s.metricBox}>
    <div style={{ fontSize: 10, color: C.light, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 22, fontWeight: 800, color: color || C.dark }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: C.light, marginTop: 2 }}>{sub}</div>}
  </div>
);

// ── Utility ───────────────────────────────────────────────────────────────────

function generateDemo(n = 756) {
  // AR(1) process mimicking a multi-year price series
  const prices = [100];
  for (let i = 1; i < n; i++) {
    prices.push(prices[i - 1] * Math.exp((Math.random() - 0.5) * 0.018));
  }
  return prices;
}

function pricesToLogRV(prices) {
  return prices.slice(1).map((p, i) => {
    const r = Math.log(p / prices[i]);
    return Math.log(r * r + 1e-12);
  });
}

function logRVToAnnVol(logRV) {
  // log_rv = log(daily_variance) → annualized_vol = sqrt(exp(log_rv)) * sqrt(252)
  return logRV.map(v => Math.sqrt(Math.exp(v)) * Math.sqrt(252));
}

function buildCumPnl(pnlArr, prices) {
  // Cumulative net P&L + buy-and-hold benchmark
  let cum = 0;
  let bhCum = 0;
  return pnlArr.map((pnl, i) => {
    cum += pnl;
    bhCum += prices && i > 0 ? Math.log(prices[i] / prices[i - 1]) : 0;
    return { i, net: cum, bh: bhCum };
  });
}

function buildDrawdown(pnlArr) {
  let cum = 0, peak = 0;
  return pnlArr.map(pnl => {
    cum += pnl;
    peak = Math.max(peak, cum);
    return { dd: -(peak - cum) };
  });
}

const fmt4 = v => (v == null ? '—' : Number(v).toFixed(4));
const fmtPct = v => (v == null ? '—' : `${(v * 100).toFixed(2)}%`);

// ── Input Panel ───────────────────────────────────────────────────────────────

function DataPanel({ onDataReady, t }) {
  const [ticker, setTicker]   = useState('VCB');
  const [period, setPeriod]   = useState('3Y');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [info, setInfo]       = useState(null);

  const load = async () => {
    setLoading(true); setError(null); setInfo(null);
    try {
      const resp = await companyService.getCompanyCharts(ticker, period);
      if (!resp.success) throw new Error(resp.error);
      const prices = (Array.isArray(resp.data) ? resp.data : [])
        .map(d => d.close ?? d.c ?? d.price).filter(v => v != null && isFinite(v));
      if (prices.length < 300) throw new Error(`Only ${prices.length} data points returned; need ≥300`);
      onDataReady(prices, ticker);
      setInfo(t('vol_forecast.input.series_info', { n: prices.length, m: prices.length - 1 }));
    } catch (e) {
      setError(t('vol_forecast.input.error_load', { msg: e.message }));
    } finally {
      setLoading(false);
    }
  };

  const demo = () => {
    const p = generateDemo(756);
    onDataReady(p, 'DEMO');
    setInfo(t('vol_forecast.input.series_info', { n: p.length, m: p.length - 1 }));
    setError(null);
  };

  return (
    <div style={s.card}>
      <div style={s.sectionTitle}>{t('vol_forecast.input.title')}</div>
      <div style={s.row}>
        <div style={s.field}>
          <span style={s.label}>{t('vol_forecast.input.ticker_label')}</span>
          <input style={s.input} value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())}
            placeholder={t('vol_forecast.input.ticker_placeholder')}
            onKeyDown={e => e.key === 'Enter' && load()} />
        </div>
        <div style={s.field}>
          <span style={s.label}>{t('vol_forecast.input.period_label')}</span>
          <select style={s.select} value={period} onChange={e => setPeriod(e.target.value)}>
            {['1Y','2Y','3Y','5Y'].map(p => (
              <option key={p} value={p}>{t(`vol_forecast.input.period_${p.toLowerCase()}`)}</option>
            ))}
          </select>
        </div>
        <button style={s.btn()} onClick={load} disabled={loading}>
          {loading ? <Spin /> : <RefreshCw size={14} />}
          {loading ? t('vol_forecast.input.loading') : t('vol_forecast.input.load_btn')}
        </button>
        <button style={s.btn(C.success)} onClick={demo}>
          <Zap size={14} />{t('vol_forecast.input.demo_btn')}
        </button>
      </div>
      {error && <div style={s.error}>{error}</div>}
      {info  && <div style={s.info}>{info}</div>}
    </div>
  );
}

// ── Config Panel ──────────────────────────────────────────────────────────────

function ConfigPanel({ cfg, setCfg, onRun, loading, hasData, t }) {
  const set = (k) => (e) => setCfg(p => ({ ...p, [k]: +e.target.value }));
  const [showAdv, setShowAdv] = useState(false);

  return (
    <div style={s.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={s.sectionTitle}>{t('vol_forecast.config.title')}</span>
        <button onClick={() => setShowAdv(p => !p)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: C.gray, display: 'flex', alignItems: 'center', gap: 4 }}>
          {showAdv ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {showAdv ? 'Hide advanced' : 'Advanced params'}
        </button>
      </div>

      {/* HAR */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: C.accent, marginBottom: 8 }}>
          {t('vol_forecast.config.har_section')}
        </div>
        <div style={s.configGrid}>
          <div style={s.field}>
            <span style={s.label}>{t('vol_forecast.config.ridge_alpha')}</span>
            <input type="number" style={s.input} min={0.1} max={50} step={0.5}
              value={cfg.har_ridge_alpha} onChange={set('har_ridge_alpha')} />
          </div>
          <div style={s.field}>
            <span style={s.label}>{t('vol_forecast.config.min_train')}</span>
            <input type="number" style={s.input} min={60} max={756} step={10}
              value={cfg.har_min_train} onChange={set('har_min_train')} />
          </div>
          <div style={s.field}>
            <span style={s.label}>{t('vol_forecast.config.refit_every')}</span>
            <input type="number" style={s.input} min={1} max={252} step={5}
              value={cfg.har_refit_every} onChange={set('har_refit_every')} />
          </div>
        </div>
      </div>

      <div style={s.divider} />

      {/* VMD-HAR */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: C.purple, marginBottom: 8 }}>
          {t('vol_forecast.config.vmd_section')}
        </div>
        <div style={s.configGrid}>
          <div style={s.field}>
            <span style={s.label}>{t('vol_forecast.config.vmd_K')}</span>
            <input type="number" style={s.input} min={2} max={10} step={1}
              value={cfg.vmd_K} onChange={set('vmd_K')} />
          </div>
          <div style={s.field}>
            <span style={s.label}>{t('vol_forecast.config.vmd_window')}</span>
            <input type="number" style={s.input} min={200} max={2000} step={100}
              value={cfg.vmd_window} onChange={set('vmd_window')} />
          </div>
          {showAdv && <>
            <div style={s.field}>
              <span style={s.label}>{t('vol_forecast.config.vmd_alpha')}</span>
              <input type="number" style={s.input} min={200} max={5000} step={200}
                value={cfg.vmd_alpha} onChange={set('vmd_alpha')} />
            </div>
            <div style={s.field}>
              <span style={s.label}>{t('vol_forecast.config.vmd_edge_lag')}</span>
              <input type="number" style={s.input} min={0} max={20} step={1}
                value={cfg.vmd_edge_lag} onChange={set('vmd_edge_lag')} />
            </div>
            <div style={s.field}>
              <span style={s.label}>{t('vol_forecast.config.ridge_alpha')} (VMD)</span>
              <input type="number" style={s.input} min={0.1} max={50} step={0.5}
                value={cfg.vmd_ridge_alpha} onChange={set('vmd_ridge_alpha')} />
            </div>
          </>}
        </div>
      </div>

      <button
        style={s.btn(loading ? C.gray : C.accent)}
        onClick={onRun}
        disabled={!hasData || loading}
      >
        {loading ? <Spin /> : <Activity size={14} />}
        {loading ? t('vol_forecast.config.running') : t('vol_forecast.config.run_btn')}
      </button>
    </div>
  );
}

// ── Forecast Comparison Panel ─────────────────────────────────────────────────

function ComparePanel({ result, t }) {
  if (!result) return null;
  const { har, vmd_har, dm_stat, winner } = result;
  const isVmdWinner = winner === 'vmd_har';

  const metricDelta = (key) => {
    const a = vmd_har.metrics[key];
    const b = har.metrics[key];
    if (a == null || b == null) return null;
    // lower is better for rmse/mae/qlike; higher for r2
    const better = key === 'r2' ? a > b : a < b;
    const pct = ((a - b) / Math.abs(b || 1)) * 100;
    return { better, pct };
  };

  const METRICS = [
    { key: 'rmse',  label: t('vol_forecast.compare.rmse'),  lowerBetter: true },
    { key: 'mae',   label: t('vol_forecast.compare.mae'),   lowerBetter: true },
    { key: 'r2',    label: t('vol_forecast.compare.r2'),    lowerBetter: false },
    { key: 'qlike', label: t('vol_forecast.compare.qlike'), lowerBetter: true },
  ];

  // Build chart data — align on common timestamps, show last 200 OOS
  const tsSet = new Set(har.timestamps);
  const common = vmd_har.timestamps.filter(t => tsSet.has(t));
  const slice = Math.min(common.length, 200);
  const harIdx  = Object.fromEntries(har.timestamps.map((t, i) => [t, i]));
  const vmdIdx  = Object.fromEntries(vmd_har.timestamps.map((t, i) => [t, i]));
  const chartData = common.slice(-slice).map(ts => ({
    ts,
    actual: har.actuals[harIdx[ts]],
    har:    har.predictions[harIdx[ts]],
    vmd:    vmd_har.predictions[vmdIdx[ts]],
  }));

  return (
    <div style={s.card}>
      {/* Winner banner */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 14px', borderRadius: 10, marginBottom: 16,
        background: isVmdWinner ? '#f0fdf4' : C.accentL,
        border: `1px solid ${isVmdWinner ? '#bbf7d0' : '#c7d2fe'}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {isVmdWinner
            ? <CheckCircle size={18} color={C.success} />
            : <Award size={18} color={C.accent} />}
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.mid }}>
              {t('vol_forecast.compare.winner_label')}
            </div>
            <div style={{ fontSize: 13, color: isVmdWinner ? C.success : C.accent }}>
              {isVmdWinner
                ? t('vol_forecast.compare.winner_vmd')
                : t('vol_forecast.compare.winner_har')}
            </div>
          </div>
        </div>
        {/* DM stat */}
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 10, color: C.light, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {t('vol_forecast.compare.dm_label')}
          </div>
          {dm_stat != null ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end', marginTop: 2 }}>
              <span style={{ fontSize: 18, fontWeight: 800, color: Math.abs(dm_stat) > 1.96 ? C.success : C.warn }}>
                {dm_stat.toFixed(3)}
              </span>
              <span style={s.badge(
                Math.abs(dm_stat) > 1.96 ? C.success : C.warn,
                Math.abs(dm_stat) > 1.96 ? '#f0fdf4' : '#fffbeb',
              )}>
                {Math.abs(dm_stat) > 1.96
                  ? t('vol_forecast.compare.dm_sig')
                  : t('vol_forecast.compare.dm_insig')}
              </span>
            </div>
          ) : <span style={{ fontSize: 13, color: C.light }}>—</span>}
        </div>
      </div>

      {/* Side-by-side metric table */}
      <div style={s.sectionTitle}>{t('vol_forecast.compare.title')}</div>
      <div style={{ overflowX: 'auto', marginBottom: 16 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              <th style={s.th}>{t('vol_forecast.compare.title').split(' ')[0]}</th>
              <th style={{ ...s.th, color: C.accent }}>{t('vol_forecast.compare.model_har')}</th>
              <th style={{ ...s.th, color: C.purple }}>{t('vol_forecast.compare.model_vmd_har')}</th>
              <th style={s.th}>Δ VMD-HAR vs HAR</th>
            </tr>
          </thead>
          <tbody>
            {METRICS.map(({ key, label, lowerBetter }) => {
              const delta = metricDelta(key);
              const vmdBetter = delta?.better;
              return (
                <tr key={key} style={{ borderBottom: `1px solid #f3f4f6` }}>
                  <td style={{ ...s.td, fontWeight: 600, color: C.mid }}>{label}</td>
                  <td style={{ ...s.td, color: C.accent, fontWeight: 700 }}>
                    {fmt4(har.metrics[key])}
                  </td>
                  <td style={{ ...s.td, color: C.purple, fontWeight: 700 }}>
                    {fmt4(vmd_har.metrics[key])}
                  </td>
                  <td style={{ ...s.td }}>
                    {delta ? (
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        color: vmdBetter ? C.success : C.danger,
                        fontWeight: 700, fontSize: 12,
                      }}>
                        {vmdBetter ? '▼' : '▲'} {Math.abs(delta.pct).toFixed(2)}%
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Forecast chart */}
      <div style={s.chartTitle}>{t('vol_forecast.compare.chart_title')}</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={s.badge()}>{t('vol_forecast.compare.oos_samples', { n: common.length })}</span>
      </div>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ left: 8, right: 16, top: 4, bottom: 0 }}>
          <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
          <XAxis dataKey="ts" tick={{ fontSize: 9, fontFamily: FONT, fill: C.gray }} tickFormatter={v => `t${v}`} />
          <YAxis tick={{ fontSize: 10, fontFamily: FONT, fill: C.gray }} />
          <Tooltip
            contentStyle={{ fontSize: 11, fontFamily: FONT, borderRadius: 6 }}
            formatter={(v, name) => {
              const labels = { actual: t('vol_forecast.compare.actual'), har: t('vol_forecast.compare.har_pred'), vmd: t('vol_forecast.compare.vmd_pred') };
              return [v?.toFixed(4), labels[name] || name];
            }}
          />
          <Legend iconSize={10} iconType="line"
            formatter={v => ({ actual: t('vol_forecast.compare.actual'), har: t('vol_forecast.compare.har_pred'), vmd: t('vol_forecast.compare.vmd_pred') }[v] || v)}
          />
          <Line type="monotone" dataKey="actual" stroke={C.dark}  strokeWidth={1.5} dot={false} isAnimationActive={false} name="actual" />
          <Line type="monotone" dataKey="har"    stroke={C.accent} strokeWidth={1.5} strokeDasharray="4 2" dot={false} isAnimationActive={false} name="har" />
          <Line type="monotone" dataKey="vmd"    stroke={C.purple} strokeWidth={1.5} strokeDasharray="2 2" dot={false} isAnimationActive={false} name="vmd" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Backtest Panel ────────────────────────────────────────────────────────────

const DEFAULT_BT = {
  model:      'vmd_har',
  target_vol: 0.15,
  max_lev:    3.0,
  cost_bps:   2.0,
};

function BacktestPanel({ compareResult, prices, t }) {
  const [cfg, setCfg]         = useState(DEFAULT_BT);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [result, setResult]   = useState(null);
  const [showPos, setShowPos] = useState(false);
  const [showTurn, setShowTurn] = useState(false);

  const canRun = compareResult && prices && prices.length > 300;

  const run = async () => {
    if (!canRun) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const fcResult = cfg.model === 'vmd_har' ? compareResult.vmd_har : compareResult.har;
      // Convert log-RV predictions to annualized vol forecasts
      const volForecast = logRVToAnnVol(fcResult.predictions);

      // Daily log-returns (aligned with OOS forecast period)
      const allReturns = prices.slice(1).map((p, i) => Math.log(p / prices[i]));

      // Align returns to forecast timestamps
      const ts = fcResult.timestamps;
      const alignedReturns = ts.map(t => allReturns[Math.min(t, allReturns.length - 1)]);

      const resp = await chartDecompService.volTargetBacktest({
        returns:       alignedReturns,
        vol_forecasts: volForecast,
        target_ann_vol: cfg.target_vol,
        max_leverage:  cfg.max_lev,
        cost_bps:      cfg.cost_bps,
      });
      const d = resp.data ?? resp;

      // Enrich with cumulative curves and drawdown
      const cumData   = buildCumPnl(d.pnl_net, alignedReturns);
      const ddData    = buildDrawdown(d.pnl_net);
      setResult({ ...d, cumData, ddData, ts });
    } catch (e) {
      setError(t('vol_forecast.backtest.error', { msg: e.response?.data?.detail ?? e.message }));
    } finally {
      setLoading(false);
    }
  };

  const mColor = (key, v) => {
    if (key === 'sharpe')   return v >= 1 ? C.success : v >= 0.5 ? C.warn : C.danger;
    if (key === 'ann_ret')  return v > 0 ? C.success : C.danger;
    if (key === 'maxdd')    return v < 0.1 ? C.success : v < 0.2 ? C.warn : C.danger;
    return C.dark;
  };

  return (
    <div style={s.card}>
      <div style={s.sectionTitle}>{t('vol_forecast.backtest.title')}</div>

      {/* Config */}
      <div style={{ ...s.cardSm, background: C.bg, marginBottom: 14 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: C.mid, marginBottom: 10 }}>
          {t('vol_forecast.backtest.config_title')}
        </div>
        <div style={s.row}>
          <div style={s.field}>
            <span style={s.label}>{t('vol_forecast.backtest.model_label')}</span>
            <select style={s.select} value={cfg.model} onChange={e => setCfg(p => ({ ...p, model: e.target.value }))}>
              <option value="har">{t('vol_forecast.compare.model_har')}</option>
              <option value="vmd_har">{t('vol_forecast.compare.model_vmd_har')}</option>
            </select>
          </div>
          <div style={s.field}>
            <span style={s.label}>{t('vol_forecast.backtest.target_vol')}</span>
            <input type="number" style={{ ...s.input, width: 80 }} min={0.05} max={0.50} step={0.01}
              value={cfg.target_vol} onChange={e => setCfg(p => ({ ...p, target_vol: +e.target.value }))} />
          </div>
          <div style={s.field}>
            <span style={s.label}>{t('vol_forecast.backtest.max_lev')}</span>
            <input type="number" style={{ ...s.input, width: 70 }} min={0.5} max={5} step={0.5}
              value={cfg.max_lev} onChange={e => setCfg(p => ({ ...p, max_lev: +e.target.value }))} />
          </div>
          <div style={s.field}>
            <span style={s.label}>{t('vol_forecast.backtest.cost_bps')}</span>
            <input type="number" style={{ ...s.input, width: 70 }} min={0} max={20} step={0.5}
              value={cfg.cost_bps} onChange={e => setCfg(p => ({ ...p, cost_bps: +e.target.value }))} />
          </div>
          <button style={s.btn(loading ? C.gray : C.accent)} onClick={run} disabled={!canRun || loading}>
            {loading ? <Spin /> : <BarChart2 size={14} />}
            {loading ? t('vol_forecast.backtest.running') : t('vol_forecast.backtest.run_btn')}
          </button>
        </div>
      </div>

      {!canRun && !loading && (
        <div style={{ padding: '24px 0', textAlign: 'center', color: C.light, fontSize: 13 }}>
          <AlertTriangle size={20} style={{ display: 'block', margin: '0 auto 6px', opacity: 0.4 }} />
          {compareResult ? t('vol_forecast.common.need_data') : t('vol_forecast.common.run_forecast_first')}
        </div>
      )}

      {error && <div style={s.error}>{error}</div>}

      {result && (() => {
        const m = result.metrics ?? {};
        const METRIC_DEFS = [
          { key: 'ann_ret',     label: t('vol_forecast.backtest.ann_ret'),  fmt: fmtPct },
          { key: 'ann_vol',     label: t('vol_forecast.backtest.ann_vol'),  fmt: fmtPct },
          { key: 'sharpe',      label: t('vol_forecast.backtest.sharpe'),   fmt: v => v?.toFixed(3) },
          { key: 'maxdd',       label: t('vol_forecast.backtest.maxdd'),    fmt: v => v?.toFixed(4) },
          { key: 'avg_leverage',label: t('vol_forecast.backtest.avg_lev'),  fmt: v => v?.toFixed(2) + 'x' },
          { key: 'ann_turnover',label: t('vol_forecast.backtest.ann_turn'), fmt: v => v?.toFixed(2) },
          { key: 'cost_drag',   label: t('vol_forecast.backtest.cost_drag'),fmt: fmtPct },
        ];

        return (
          <>
            {/* Metric cards */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
              {METRIC_DEFS.map(({ key, label, fmt }) => (
                <MetricCard key={key} label={label} value={fmt(m[key])} color={mColor(key, m[key])} />
              ))}
            </div>

            {/* Equity curve */}
            <div style={{ marginBottom: 16 }}>
              <div style={s.chartTitle}>{t('vol_forecast.backtest.equity_title')}</div>
              <ResponsiveContainer width="100%" height={340}>
                <ComposedChart data={result.cumData} margin={{ left: 8, right: 16, top: 4, bottom: 0 }}>
                  <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
                  <XAxis dataKey="i" tick={{ fontSize: 9, fill: C.gray }} tickFormatter={v => `t${v}`} />
                  <YAxis tick={{ fontSize: 10, fill: C.gray }} tickFormatter={v => v.toFixed(3)} />
                  <Tooltip contentStyle={{ fontSize: 11, borderRadius: 6 }}
                    formatter={(v, n) => [v?.toFixed(5), n === 'net' ? t('vol_forecast.backtest.net_label') : t('vol_forecast.backtest.benchmark_label')]} />
                  <Legend iconSize={10}
                    formatter={n => n === 'net' ? t('vol_forecast.backtest.net_label') : t('vol_forecast.backtest.benchmark_label')} />
                  <ReferenceLine y={0} stroke={C.gray} strokeDasharray="3 3" />
                  <Line type="monotone" dataKey="bh" stroke={C.light} strokeWidth={1} dot={false} strokeDasharray="4 2" isAnimationActive={false} name="bh" />
                  <Area type="monotone" dataKey="net" stroke={C.accent} strokeWidth={2}
                    fill={C.accentL} dot={false} isAnimationActive={false} name="net" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* Drawdown */}
            <div style={{ marginBottom: 16 }}>
              <div style={s.chartTitle}>{t('vol_forecast.backtest.drawdown_title')}</div>
              <ResponsiveContainer width="100%" height={120}>
                <AreaChart data={result.ddData} margin={{ left: 8, right: 16, top: 4, bottom: 0 }}>
                  <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="i" hide />
                  <YAxis tick={{ fontSize: 9, fill: C.gray }} tickFormatter={v => v.toFixed(3)} />
                  <Tooltip contentStyle={{ fontSize: 11, borderRadius: 6 }} formatter={v => [v?.toFixed(5), 'Drawdown']} />
                  <Area type="monotone" dataKey="dd" stroke={C.danger} fill="rgba(239,68,68,0.15)"
                    strokeWidth={1.5} dot={false} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Collapsible position chart */}
            <div style={{ marginBottom: 8 }}>
              <button onClick={() => setShowPos(p => !p)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 700, color: C.mid, display: 'flex', alignItems: 'center', gap: 4, padding: '4px 0' }}>
                {showPos ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                {t('vol_forecast.backtest.position_title')}
              </button>
              {showPos && (
                <ResponsiveContainer width="100%" height={120}>
                  <ComposedChart data={result.positions.map((w, i) => ({ i, w }))} margin={{ left: 8, right: 16, top: 4, bottom: 0 }}>
                    <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="i" hide />
                    <YAxis tick={{ fontSize: 9, fill: C.gray }} />
                    <Tooltip formatter={v => [v?.toFixed(3), 'w[t]']} contentStyle={{ fontSize: 11 }} />
                    <ReferenceLine y={0} stroke={C.gray} />
                    <Bar dataKey="w" fill={C.accent} opacity={0.6} isAnimationActive={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Collapsible turnover chart */}
            <div>
              <button onClick={() => setShowTurn(p => !p)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 700, color: C.mid, display: 'flex', alignItems: 'center', gap: 4, padding: '4px 0' }}>
                {showTurn ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                {t('vol_forecast.backtest.turnover_title')}
              </button>
              {showTurn && (
                <ResponsiveContainer width="100%" height={100}>
                  <AreaChart data={result.turnover.map((v, i) => ({ i, v }))} margin={{ left: 8, right: 16, top: 4, bottom: 0 }}>
                    <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="i" hide />
                    <YAxis tick={{ fontSize: 9, fill: C.gray }} tickFormatter={v => v.toFixed(2)} />
                    <Tooltip formatter={v => [v?.toFixed(4), 'Turnover']} contentStyle={{ fontSize: 11 }} />
                    <Area type="monotone" dataKey="v" stroke={C.sky} fill="rgba(14,165,233,0.12)"
                      strokeWidth={1} dot={false} isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </>
        );
      })()}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const DEFAULT_CFG = {
  har_ridge_alpha: 5,   har_min_train: 252, har_refit_every: 60,
  vmd_K: 4, vmd_alpha: 2000, vmd_window: 1000, vmd_edge_lag: 5,
  vmd_ridge_alpha: 5, vmd_min_train: 252, vmd_refit_vmd_every: 20, vmd_refit_model_every: 60,
};

export default function VolForecastPage() {
  const { t } = useTranslation();
  const [prices, setPrices]           = useState(null);
  const [logRV, setLogRV]             = useState(null);
  const [cfg, setCfg]                 = useState(DEFAULT_CFG);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState(null);
  const [compareResult, setCompare]   = useState(null);

  const onDataReady = useCallback((p) => {
    setPrices(p);
    setLogRV(pricesToLogRV(p));
    setCompare(null);
  }, []);

  const runCompare = async () => {
    if (!logRV || logRV.length < 300) {
      setError(t('vol_forecast.common.need_data')); return;
    }
    setLoading(true); setError(null); setCompare(null);
    try {
      const resp = await chartDecompService.forecastCompare({
        log_rv: logRV,
        har: {
          ridge_alpha: cfg.har_ridge_alpha,
          min_train:   cfg.har_min_train,
          refit_every: cfg.har_refit_every,
        },
        vmd: {
          K:                 cfg.vmd_K,
          alpha:             cfg.vmd_alpha,
          window:            cfg.vmd_window,
          edge_lag:          cfg.vmd_edge_lag,
          ridge_alpha:       cfg.vmd_ridge_alpha,
          min_train:         cfg.vmd_min_train,
          refit_vmd_every:   cfg.vmd_refit_vmd_every,
          refit_model_every: cfg.vmd_refit_model_every,
        },
      });
      setCompare(resp.data ?? resp);
    } catch (e) {
      setError(t('vol_forecast.config.error', { msg: e.response?.data?.detail ?? e.message }));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={s.page}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <TrendingUp size={22} color={C.accent} />
          <h1 style={{ fontSize: 22, fontWeight: 800, color: C.dark, margin: 0 }}>
            {t('vol_forecast.page_title')}
          </h1>
        </div>
        <p style={{ fontSize: 13, color: C.gray, marginTop: 4 }}>
          {t('vol_forecast.page_subtitle')}
        </p>
      </div>

      {/* Data input */}
      <DataPanel onDataReady={onDataReady} t={t} />

      {/* Model config + run */}
      <ConfigPanel
        cfg={cfg} setCfg={setCfg}
        onRun={runCompare} loading={loading}
        hasData={!!logRV}
        t={t}
      />

      {error && <div style={{ ...s.error, marginBottom: 16 }}>{error}</div>}

      {/* Forecast comparison results */}
      {compareResult && <ComparePanel result={compareResult} t={t} />}

      {/* Backtest */}
      <BacktestPanel compareResult={compareResult} prices={prices} t={t} />
    </div>
  );
}
