// CD-3 — Chart Decomposition & Multi-Scale Analysis viewer
// Tabs: Signal Decomposition | Time-Frequency | Hurst & Coherence | Volatility Forecast
import React, { useState, useRef, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ReferenceArea,
} from 'recharts';
import { Activity, RefreshCw, TrendingUp, Zap, BarChart2, GitBranch } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import chartDecompService from '../../../services/chartDecompService';
import companyService from '../../../services/companyService';

// ── Palette & theme ───────────────────────────────────────────────────────────

const COLORS = {
  original:    '#111827',
  approx:      '#3b82f6',
  details:     ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#fb923c'],
  grid:        '#e5e7eb',
  gridDash:    '3 3',
  axis:        '#6b7280',
  bg:          '#f9fafb',
  card:        '#ffffff',
  border:      '#e5e7eb',
  accent:      '#6366f1',
  accentLight: '#eef2ff',
  coi:         'rgba(100,100,100,0.18)',
  success:     '#10b981',
  warn:        '#f59e0b',
  danger:      '#ef4444',
};

const FONT = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";

// Viridis-like color scale for scalogram (0=dark blue → 1=yellow)
function scaleColor(t) {
  const stops = [
    [68,  1,  84],
    [59,  82, 139],
    [33, 145, 140],
    [94, 201,  98],
    [253, 231,  37],
  ];
  const idx = t * (stops.length - 1);
  const lo  = Math.floor(idx);
  const hi  = Math.min(lo + 1, stops.length - 1);
  const frac = idx - lo;
  const r = Math.round(stops[lo][0] + (stops[hi][0] - stops[lo][0]) * frac);
  const g = Math.round(stops[lo][1] + (stops[hi][1] - stops[lo][1]) * frac);
  const b = Math.round(stops[lo][2] + (stops[hi][2] - stops[lo][2]) * frac);
  return `rgb(${r},${g},${b})`;
}

// ── Shared sub-components ─────────────────────────────────────────────────────

const s = {
  page: { background: COLORS.bg, minHeight: '100vh', padding: '20px 24px', fontFamily: FONT },
  header: { marginBottom: 20 },
  h1: { fontSize: 22, fontWeight: 800, color: '#111827', margin: 0 },
  subtitle: { fontSize: 13, color: '#6b7280', marginTop: 4 },
  card: {
    background: COLORS.card, border: `1px solid ${COLORS.border}`,
    borderRadius: 12, padding: '16px 20px', marginBottom: 16,
  },
  cardTitle: { fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#374151', marginBottom: 12 },
  row: { display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' },
  field: { display: 'flex', flexDirection: 'column', gap: 4 },
  label: { fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' },
  input: {
    height: 36, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: '0 10px',
    fontSize: 13, fontFamily: FONT, color: '#111827', outline: 'none', background: '#fff',
    minWidth: 100,
  },
  select: {
    height: 36, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: '0 8px',
    fontSize: 13, fontFamily: FONT, color: '#111827', background: '#fff', cursor: 'pointer',
  },
  btn: (color = COLORS.accent, light = false) => ({
    height: 36, padding: '0 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
    fontSize: 13, fontWeight: 600, fontFamily: FONT,
    background: light ? COLORS.accentLight : color,
    color: light ? COLORS.accent : '#fff',
    display: 'flex', alignItems: 'center', gap: 6,
    transition: 'opacity 0.15s',
  }),
  tabBar: { display: 'flex', gap: 0, borderBottom: `2px solid ${COLORS.border}`, marginBottom: 20 },
  tab: (active) => ({
    padding: '10px 18px', cursor: 'pointer', fontSize: 13, fontWeight: 600, fontFamily: FONT,
    color: active ? COLORS.accent : '#6b7280',
    borderBottom: active ? `2px solid ${COLORS.accent}` : '2px solid transparent',
    marginBottom: -2, transition: 'all 0.15s', background: 'none', border: 'none',
    borderBottomStyle: 'solid', borderBottomWidth: 2,
    borderBottomColor: active ? COLORS.accent : 'transparent',
  }),
  errorBox: { background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', fontSize: 13, color: '#b91c1c' },
  infoBox: { background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: '10px 14px', fontSize: 13, color: '#166534' },
  emptyBox: { padding: '48px 0', textAlign: 'center', color: '#9ca3af', fontSize: 14 },
  badge: (color = '#6b7280', bg = '#f3f4f6') => ({
    display: 'inline-flex', alignItems: 'center', gap: 4,
    padding: '2px 8px', borderRadius: 99, fontSize: 11, fontWeight: 700,
    color, background: bg,
  }),
  metricCard: {
    flex: 1, minWidth: 120, background: '#f9fafb', border: `1px solid ${COLORS.border}`,
    borderRadius: 10, padding: '12px 16px',
  },
  chartTitle: { fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' },
};

const Spinner = () => (
  <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />
);

const MetricCard = ({ label, value, color }) => (
  <div style={s.metricCard}>
    <div style={{ fontSize: 10, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 20, fontWeight: 800, color: color || '#111827' }}>{value}</div>
  </div>
);

const EmptyState = ({ text }) => (
  <div style={s.emptyBox}><Activity size={32} style={{ margin: '0 auto 8px', display: 'block', opacity: 0.3 }} />{text}</div>
);

// ── Input Panel ───────────────────────────────────────────────────────────────

function generateDemoSeries(n = 512) {
  // AR(1) + harmonic + trend — mimics log-price behavior
  const x = new Array(n);
  let val = 0;
  for (let i = 0; i < n; i++) {
    val = 0.98 * val + (Math.random() - 0.5) * 0.8;
    const season = 0.6 * Math.sin(2 * Math.PI * i / 63) + 0.3 * Math.sin(2 * Math.PI * i / 21);
    x[i] = val + season + i * 0.003;
  }
  return x;
}

function InputPanel({ onSeriesReady, t }) {
  const [ticker, setTicker]   = useState('VCB');
  const [period, setPeriod]   = useState('2Y');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [info, setInfo]       = useState(null);

  const loadTicker = async () => {
    setLoading(true); setError(null); setInfo(null);
    try {
      const resp = await companyService.getCompanyCharts(ticker, period);
      if (!resp.success) throw new Error(resp.error);
      // stock-data-service returns { symbol, name, exchange, data: [...], count }.
      // Older mocks returned a bare array, so accept both shapes.
      const raw = resp.data;
      const rows = Array.isArray(raw)
        ? raw
        : Array.isArray(raw?.data) ? raw.data : [];
      const prices = rows
        .map(d => d.close ?? d.c ?? d.price)
        .filter(v => v != null && isFinite(v));
      if (prices.length < 64) throw new Error('Not enough price data returned');
      onSeriesReady(prices, ticker);
      setInfo(t('chart_decomp.input.series_info', { n: prices.length }));
    } catch (e) {
      setError(t('chart_decomp.input.error_load', { msg: e.message }));
    } finally {
      setLoading(false);
    }
  };

  const loadDemo = () => {
    const x = generateDemoSeries(512);
    onSeriesReady(x, 'DEMO');
    setInfo(t('chart_decomp.input.series_info', { n: x.length }));
    setError(null);
  };

  return (
    <div style={s.card}>
      <div style={s.cardTitle}>{t('chart_decomp.input.title')}</div>
      <div style={s.row}>
        <div style={s.field}>
          <span style={s.label}>{t('chart_decomp.input.ticker_label')}</span>
          <input
            style={s.input}
            value={ticker}
            onChange={e => setTicker(e.target.value.toUpperCase())}
            placeholder={t('chart_decomp.input.ticker_placeholder')}
            onKeyDown={e => e.key === 'Enter' && loadTicker()}
          />
        </div>
        <div style={s.field}>
          <span style={s.label}>{t('chart_decomp.input.period_label')}</span>
          <select style={s.select} value={period} onChange={e => setPeriod(e.target.value)}>
            <option value="1Y">{t('chart_decomp.input.period_1y')}</option>
            <option value="2Y">{t('chart_decomp.input.period_2y')}</option>
            <option value="3Y">{t('chart_decomp.input.period_3y')}</option>
            <option value="5Y">{t('chart_decomp.input.period_5y')}</option>
          </select>
        </div>
        <button style={s.btn()} onClick={loadTicker} disabled={loading}>
          {loading ? <Spinner /> : <RefreshCw size={14} />}
          {loading ? t('chart_decomp.input.loading') : t('chart_decomp.input.load_btn')}
        </button>
        <button style={s.btn(COLORS.success)} onClick={loadDemo}>
          <Zap size={14} />{t('chart_decomp.input.demo_btn')}
        </button>
      </div>
      {error && <div style={{ ...s.errorBox, marginTop: 10 }}>{error}</div>}
      {info  && <div style={{ ...s.infoBox,  marginTop: 10 }}>{info}</div>}
    </div>
  );
}

// ── Decomposition Tab ─────────────────────────────────────────────────────────

function ComponentChart({ title, data, color, height = 90, showCoi, coiWidth }) {
  const chartData = data.map((v, i) => ({ i, v }));
  const N = data.length;
  const coiLeft  = coiWidth != null ? coiWidth : 0;
  const coiRight = coiWidth != null ? N - 1 - coiWidth : N - 1;

  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#374151', marginBottom: 2, marginLeft: 4 }}>{title}</div>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
          <CartesianGrid stroke={COLORS.grid} strokeDasharray={COLORS.gridDash} vertical={false} />
          <XAxis dataKey="i" hide tick={false} />
          <YAxis
            tick={{ fontSize: 9, fontFamily: FONT, fill: COLORS.axis }}
            width={40}
            tickFormatter={v => v.toFixed(1)}
          />
          <Tooltip
            formatter={v => [v.toFixed(4), title]}
            labelFormatter={i => `t=${i}`}
            contentStyle={{ fontSize: 11, fontFamily: FONT, borderRadius: 6 }}
          />
          {showCoi && coiLeft > 0 && (
            <ReferenceLine x={coiLeft}  stroke={COLORS.coi} strokeWidth={1} strokeDasharray="4 2" />
          )}
          {showCoi && coiRight < N - 1 && (
            <ReferenceLine x={coiRight} stroke={COLORS.coi} strokeWidth={1} strokeDasharray="4 2" />
          )}
          <Line
            type="monotone" dataKey="v" stroke={color} strokeWidth={1.2}
            dot={false} isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function DecompTab({ series, t }) {
  const [method, setMethod]   = useState('modwt');
  const [wavelet, setWavelet] = useState('sym8');
  const [level, setLevel]     = useState(6);
  const [K, setK]             = useState(5);
  const [alpha, setAlpha]     = useState(1500);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [result, setResult]   = useState(null);

  const run = async () => {
    if (!series) return;
    setLoading(true); setError(null); setResult(null);
    try {
      let resp;
      if (method === 'modwt') resp = await chartDecompService.modwt({ series, wavelet, level });
      else if (method === 'emd')  resp = await chartDecompService.emd({ series });
      else if (method === 'eemd') resp = await chartDecompService.eemd({ series });
      else                         resp = await chartDecompService.vmd({ series, K, alpha });
      setResult({ method, data: resp.data ?? resp });
    } catch (e) {
      setError(t('chart_decomp.decomp.error', { msg: e.response?.data?.detail ?? e.message }));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Controls */}
      <div style={s.card}>
        <div style={s.row}>
          <div style={s.field}>
            <span style={s.label}>{t('chart_decomp.decomp.method_label')}</span>
            <select style={s.select} value={method} onChange={e => setMethod(e.target.value)}>
              <option value="modwt">{t('chart_decomp.decomp.method_modwt')}</option>
              <option value="emd">{t('chart_decomp.decomp.method_emd')}</option>
              <option value="eemd">{t('chart_decomp.decomp.method_eemd')}</option>
              <option value="vmd">{t('chart_decomp.decomp.method_vmd')}</option>
            </select>
          </div>
          {method === 'modwt' && <>
            <div style={s.field}>
              <span style={s.label}>{t('chart_decomp.decomp.wavelet_label')}</span>
              <select style={s.select} value={wavelet} onChange={e => setWavelet(e.target.value)}>
                {['sym8','sym4','db4','db8','haar','coif3'].map(w => (
                  <option key={w} value={w}>{w}</option>
                ))}
              </select>
            </div>
            <div style={s.field}>
              <span style={s.label}>{t('chart_decomp.decomp.level_label')}</span>
              <input type="number" style={{ ...s.input, width: 64 }} min={2} max={10}
                value={level} onChange={e => setLevel(+e.target.value)} />
            </div>
          </>}
          {method === 'vmd' && <>
            <div style={s.field}>
              <span style={s.label}>{t('chart_decomp.decomp.modes_label')}</span>
              <input type="number" style={{ ...s.input, width: 64 }} min={2} max={12}
                value={K} onChange={e => setK(+e.target.value)} />
            </div>
            <div style={s.field}>
              <span style={s.label}>{t('chart_decomp.decomp.alpha_label')}</span>
              <input type="number" style={{ ...s.input, width: 80 }} min={200} max={5000} step={100}
                value={alpha} onChange={e => setAlpha(+e.target.value)} />
            </div>
          </>}
          <button
            style={s.btn(loading ? '#9ca3af' : COLORS.accent)}
            onClick={run}
            disabled={!series || loading}
          >
            {loading ? <Spinner /> : <Activity size={14} />}
            {loading ? t('chart_decomp.decomp.running') : t('chart_decomp.decomp.run_btn')}
          </button>
        </div>
        {error && <div style={{ ...s.errorBox, marginTop: 10 }}>{error}</div>}
      </div>

      {/* Results */}
      {!result && !loading && (
        <EmptyState text={series ? t('chart_decomp.common.run_first') : t('chart_decomp.input.no_data')} />
      )}

      {result && (() => {
        const d = result.data;

        if (result.method === 'modwt') {
          const components = [
            { label: t('chart_decomp.decomp.original_label'), data: series, color: COLORS.original, height: 100 },
            { label: t('chart_decomp.decomp.approx_label', { j: d.level }), data: d.approximation, color: COLORS.approx, coi: d.coi_widths?.[d.level - 1] },
            ...d.details.map((det, i) => ({
              label: t('chart_decomp.decomp.detail_label', { j: i + 1 }),
              data: det,
              color: COLORS.details[i % COLORS.details.length],
              coi: d.coi_widths?.[i],
            })),
          ];
          return (
            <div style={s.card}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <span style={s.cardTitle}>MODWT — {wavelet}, J={d.level}</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <span style={s.badge(COLORS.success, '#f0fdf4')}>
                    {t('chart_decomp.decomp.recon_error')}: {d.reconstruction_error?.toExponential(2)}
                  </span>
                  <span style={s.badge()}>{t('chart_decomp.decomp.n_components', { n: d.level + 1 })}</span>
                </div>
              </div>
              <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 10 }}>
                {t('chart_decomp.decomp.coi_note')}
              </div>
              {components.map((c, idx) => (
                <ComponentChart
                  key={idx}
                  title={c.label}
                  data={c.data}
                  color={c.color}
                  height={idx === 0 ? 110 : 80}
                  showCoi={c.coi != null}
                  coiWidth={c.coi}
                />
              ))}
            </div>
          );
        }

        if (result.method === 'vmd') {
          return (
            <div style={s.card}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <span style={s.cardTitle}>VMD — K={d.n_modes}</span>
                <span style={s.badge(COLORS.warn, '#fffbeb')}>
                  {t('chart_decomp.decomp.recon_error')}: {d.reconstruction_error?.toExponential(2)}
                </span>
              </div>
              <ComponentChart title={t('chart_decomp.decomp.original_label')} data={series} color={COLORS.original} height={110} />
              {d.modes.map((mode, i) => (
                <ComponentChart
                  key={i}
                  title={`${t('chart_decomp.decomp.mode_label', { j: i + 1 })} ω=${d.omega_final[i]?.toFixed(4)}`}
                  data={mode}
                  color={COLORS.details[i % COLORS.details.length]}
                  height={80}
                />
              ))}
            </div>
          );
        }

        // EMD / EEMD
        return (
          <div style={s.card}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={s.cardTitle}>{result.method.toUpperCase()} — {d.n_imfs} IMFs</span>
              <span style={s.badge(COLORS.success, '#f0fdf4')}>
                {t('chart_decomp.decomp.recon_error')}: {d.reconstruction_error?.toExponential(2)}
              </span>
            </div>
            <ComponentChart title={t('chart_decomp.decomp.original_label')} data={series} color={COLORS.original} height={110} />
            {d.imfs.slice(0, -1).map((imf, i) => (
              <ComponentChart
                key={i}
                title={t('chart_decomp.decomp.imf_label', { j: i + 1 })}
                data={imf}
                color={COLORS.details[i % COLORS.details.length]}
                height={80}
              />
            ))}
            <ComponentChart
              title={t('chart_decomp.decomp.residue_label')}
              data={d.imfs[d.imfs.length - 1]}
              color="#9ca3af"
              height={80}
            />
          </div>
        );
      })()}
    </div>
  );
}

// ── Time-Frequency Tab ────────────────────────────────────────────────────────

function ScalogramCanvas({ power, frequencies, coi }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!power || !power.length) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const nFreqs = power.length;
    const N      = power[0].length;

    // Find max power for normalization (log scale looks better)
    let maxP = 0;
    for (let fi = 0; fi < nFreqs; fi++)
      for (let ti = 0; ti < N; ti++)
        if (power[fi][ti] > maxP) maxP = power[fi][ti];

    const W = canvas.width;
    const H = canvas.height;
    const cellW = W / N;
    const cellH = H / nFreqs;

    // Draw heatmap
    for (let fi = 0; fi < nFreqs; fi++) {
      for (let ti = 0; ti < N; ti++) {
        const t = maxP > 0 ? Math.sqrt(power[fi][ti] / maxP) : 0; // sqrt for perceptual balance
        ctx.fillStyle = scaleColor(t);
        ctx.fillRect(Math.floor(ti * cellW), Math.floor(fi * cellH), Math.ceil(cellW), Math.ceil(cellH));
      }
    }

    // COI overlay — everything OUTSIDE COI gets a semi-transparent dark mask
    if (coi && coi.length === N) {
      ctx.fillStyle = 'rgba(0,0,0,0.38)';
      for (let ti = 0; ti < N; ti++) {
        const maxPeriod = coi[ti]; // max reliable period at this time
        for (let fi = 0; fi < nFreqs; fi++) {
          const period = frequencies[fi] > 0 ? 1 / frequencies[fi] : Infinity;
          if (period > maxPeriod) {
            ctx.fillRect(Math.floor(ti * cellW), Math.floor(fi * cellH), Math.ceil(cellW), Math.ceil(cellH));
          }
        }
      }
    }
  }, [power, frequencies, coi]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={260}
      style={{ width: '100%', height: 260, imageRendering: 'pixelated', borderRadius: 6, display: 'block' }}
    />
  );
}

function ColorBar() {
  const { t } = useTranslation();
  const stops = [0, 0.25, 0.5, 0.75, 1];
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
      <span style={{ fontSize: 10, color: COLORS.axis }}>{t('chart_decomp.time_freq.low_power')}</span>
      <div style={{
        height: 12, flex: 1, borderRadius: 4, maxWidth: 180,
        background: `linear-gradient(to right, ${stops.map(t => scaleColor(t)).join(',')})`
      }} />
      <span style={{ fontSize: 10, color: COLORS.axis }}>{t('chart_decomp.time_freq.high_power')}</span>
    </div>
  );
}

function TimeFreqTab({ series, t }) {
  const [method, setMethod]   = useState('cwt');
  const [nScales, setNScales] = useState(64);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [result, setResult]   = useState(null);

  const run = async () => {
    if (!series) return;
    setLoading(true); setError(null); setResult(null);
    try {
      let resp;
      if (method === 'cwt') {
        resp = await chartDecompService.cwt({ series, n_scales: nScales });
      } else {
        resp = await chartDecompService.hht({ series });
      }
      setResult({ method, data: resp.data ?? resp });
    } catch (e) {
      setError(t('chart_decomp.time_freq.error', { msg: e.response?.data?.detail ?? e.message }));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={s.card}>
        <div style={s.row}>
          <div style={s.field}>
            <span style={s.label}>{t('chart_decomp.decomp.method_label')}</span>
            <select style={s.select} value={method} onChange={e => setMethod(e.target.value)}>
              <option value="cwt">{t('chart_decomp.time_freq.method_cwt')}</option>
              <option value="hht">{t('chart_decomp.time_freq.method_hht')}</option>
            </select>
          </div>
          {method === 'cwt' && (
            <div style={s.field}>
              <span style={s.label}>{t('chart_decomp.time_freq.n_scales_label')}</span>
              <select style={s.select} value={nScales} onChange={e => setNScales(+e.target.value)}>
                {[32, 64, 128].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
          )}
          <button
            style={s.btn(loading ? '#9ca3af' : COLORS.accent)}
            onClick={run}
            disabled={!series || loading}
          >
            {loading ? <Spinner /> : <BarChart2 size={14} />}
            {loading ? t('chart_decomp.time_freq.running') : t('chart_decomp.time_freq.run_btn')}
          </button>
        </div>
        {error && <div style={{ ...s.errorBox, marginTop: 10 }}>{error}</div>}
      </div>

      {!result && !loading && (
        <EmptyState text={series ? t('chart_decomp.common.run_first') : t('chart_decomp.input.no_data')} />
      )}

      {result && (() => {
        const d = result.data;
        const nf = d.frequencies?.length ?? 0;
        const freqLabels = d.frequencies?.map(f => (f > 0 ? (1 / f).toFixed(0) : '∞')) ?? [];
        return (
          <div style={s.card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={s.cardTitle}>
                {result.method === 'cwt'
                  ? t('chart_decomp.time_freq.method_cwt')
                  : t('chart_decomp.time_freq.method_hht')}
                {' '}— {nf} {t('chart_decomp.time_freq.n_scales_label').toLowerCase()}
              </span>
              <span style={s.badge(COLORS.accent, COLORS.accentLight)}>
                COI {t('chart_decomp.decomp.coi_note').split(':')[0]}
              </span>
            </div>
            {/* Scalogram */}
            <div style={{ position: 'relative' }}>
              <div style={{ display: 'flex', gap: 8 }}>
                {/* Y-axis labels (period) */}
                <div style={{ width: 44, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', paddingBottom: 4 }}>
                  {[0, Math.floor(nf / 4), Math.floor(nf / 2), Math.floor(3 * nf / 4), nf - 1]
                    .filter(i => i < freqLabels.length)
                    .map((i, idx) => (
                      <span key={idx} style={{ fontSize: 9, color: COLORS.axis, textAlign: 'right' }}>
                        {freqLabels[i]}
                      </span>
                    ))}
                </div>
                <div style={{ flex: 1 }}>
                  <ScalogramCanvas power={d.power} frequencies={d.frequencies} coi={d.coi} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 2 }}>
                    <span style={{ fontSize: 9, color: COLORS.axis }}>0</span>
                    <span style={{ fontSize: 9, color: COLORS.axis, textAlign: 'center' }}>
                      {t('chart_decomp.time_freq.time_axis')}
                    </span>
                    <span style={{ fontSize: 9, color: COLORS.axis }}>{series?.length}</span>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
                <span style={{ fontSize: 10, color: '#9ca3af' }}>
                  {t('chart_decomp.time_freq.period_axis')}
                </span>
                <ColorBar />
              </div>
            </div>
            {/* Original series minimap */}
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#374151', marginBottom: 4 }}>
                {t('chart_decomp.decomp.original_label')}
              </div>
              <ResponsiveContainer width="100%" height={60}>
                <LineChart data={(series ?? []).map((v, i) => ({ i, v }))} margin={{ left: 44, right: 0, top: 0, bottom: 0 }}>
                  <XAxis dataKey="i" hide />
                  <YAxis hide />
                  <Line type="monotone" dataKey="v" stroke={COLORS.original} strokeWidth={1} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        );
      })()}
    </div>
  );
}

// ── Hurst & Coherence Tab ─────────────────────────────────────────────────────

function HurstTab({ series, t }) {
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);
  const [result, setResult]       = useState(null);
  const [cohLoading, setCohLoading] = useState(false);
  const [cohError, setCohError]   = useState(null);
  const [cohResult, setCohResult] = useState(null);
  const [ticker2, setTicker2]     = useState('');
  const [series2, setSeries2]     = useState(null);
  const [loadingS2, setLoadingS2] = useState(false);

  const runHurst = async () => {
    if (!series) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const resp = await chartDecompService.hurst({ series });
      setResult(resp.data ?? resp);
    } catch (e) {
      setError(t('chart_decomp.hurst.error', { msg: e.response?.data?.detail ?? e.message }));
    } finally {
      setLoading(false);
    }
  };

  const loadSecondSeries = async () => {
    if (!ticker2) return;
    setLoadingS2(true);
    try {
      const resp = await companyService.getCompanyCharts(ticker2, '2Y');
      if (!resp.success) throw new Error(resp.error);
      const prices = (Array.isArray(resp.data) ? resp.data : [])
        .map(d => d.close ?? d.c ?? d.price)
        .filter(v => v != null && isFinite(v));
      setSeries2(prices);
    } catch (e) {
      setCohError(t('chart_decomp.input.error_load', { msg: e.message }));
    } finally {
      setLoadingS2(false);
    }
  };

  const runCoherence = async () => {
    if (!series || !series2) return;
    const N = Math.min(series.length, series2.length);
    setCohLoading(true); setCohError(null); setCohResult(null);
    try {
      const resp = await chartDecompService.coherence({ x: series.slice(-N), y: series2.slice(-N) });
      setCohResult(resp.data ?? resp);
    } catch (e) {
      setCohError(t('chart_decomp.hurst.error', { msg: e.response?.data?.detail ?? e.message }));
    } finally {
      setCohLoading(false);
    }
  };

  const hrstColor = (H) => {
    if (H == null) return '#6b7280';
    if (H > 0.6) return COLORS.danger;
    if (H < 0.4) return '#3b82f6';
    return COLORS.success;
  };

  const hrstLabel = (H, t) => {
    if (H == null) return '';
    if (H > 0.6) return t('chart_decomp.hurst.h_trend');
    if (H < 0.4) return t('chart_decomp.hurst.h_mr');
    return t('chart_decomp.hurst.h_random');
  };

  return (
    <div>
      {/* Hurst panel */}
      <div style={s.card}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <span style={s.cardTitle}>{t('chart_decomp.hurst.variance_plot_title')}</span>
          <button
            style={s.btn(loading ? '#9ca3af' : COLORS.accent)}
            onClick={runHurst}
            disabled={!series || loading}
          >
            {loading ? <Spinner /> : <TrendingUp size={14} />}
            {loading ? t('chart_decomp.hurst.running') : t('chart_decomp.hurst.run_btn')}
          </button>
        </div>
        {error && <div style={s.errorBox}>{error}</div>}
        {!result && !loading && (
          <EmptyState text={series ? t('chart_decomp.common.run_first') : t('chart_decomp.input.no_data')} />
        )}
        {result && (() => {
          const H = result.hurst;
          const vData = (result.variances ?? []).map((v, i) => ({ level: i + 1, logV: Math.log2(Math.max(v, 1e-30)) }));
          return (
            <>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
                <div style={s.metricCard}>
                  <div style={{ fontSize: 10, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                    {t('chart_decomp.hurst.h_label')}
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 900, color: hrstColor(H) }}>{H?.toFixed(4)}</div>
                  <div style={{ fontSize: 11, color: hrstColor(H), marginTop: 2, fontWeight: 600 }}>
                    {hrstLabel(H, t)}
                  </div>
                </div>
                <MetricCard label={t('chart_decomp.hurst.slope_label')} value={result.slope?.toFixed(4)} />
                <MetricCard label={t('chart_decomp.hurst.intercept_label')} value={result.intercept?.toFixed(4)} />
              </div>
              {/* Variance-by-scale chart */}
              <div style={s.chartTitle}>{t('chart_decomp.hurst.variance_plot_title')}</div>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={vData} margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                  <CartesianGrid stroke={COLORS.grid} strokeDasharray={COLORS.gridDash} />
                  <XAxis dataKey="level" tick={{ fontSize: 10, fontFamily: FONT, fill: COLORS.axis }}
                    label={{ value: 'j (level)', position: 'insideBottom', offset: -2, fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10, fontFamily: FONT, fill: COLORS.axis }}
                    label={{ value: 'log₂ Var', angle: -90, position: 'insideLeft', fontSize: 10 }} />
                  <Tooltip formatter={v => [v.toFixed(3), 'log₂ Var']} contentStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="logV" stroke={COLORS.accent} strokeWidth={2}
                    dot={{ r: 4, fill: COLORS.accent }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </>
          );
        })()}
      </div>

      {/* Coherence panel */}
      <div style={s.card}>
        <div style={s.cardTitle}>{t('chart_decomp.hurst.coherence_title')}</div>
        <div style={s.row}>
          <div style={s.field}>
            <span style={s.label}>{t('chart_decomp.hurst.coherence_ticker2')}</span>
            <input
              style={s.input}
              value={ticker2}
              onChange={e => setTicker2(e.target.value.toUpperCase())}
              placeholder="VD: TCB, HPG…"
              onKeyDown={e => e.key === 'Enter' && loadSecondSeries()}
            />
          </div>
          <button style={s.btn(COLORS.success)} onClick={loadSecondSeries} disabled={!ticker2 || loadingS2}>
            {loadingS2 ? <Spinner /> : <RefreshCw size={14} />}
            {loadingS2 ? t('chart_decomp.input.loading') : t('chart_decomp.input.load_btn')}
          </button>
          {series2 && (
            <span style={s.badge(COLORS.success, '#f0fdf4')}>
              {t('chart_decomp.input.series_info', { n: series2.length })}
            </span>
          )}
          <button
            style={s.btn(cohLoading ? '#9ca3af' : COLORS.accent)}
            onClick={runCoherence}
            disabled={!series || !series2 || cohLoading}
          >
            {cohLoading ? <Spinner /> : <GitBranch size={14} />}
            {cohLoading ? t('chart_decomp.hurst.coherence_running') : t('chart_decomp.hurst.coherence_run')}
          </button>
        </div>
        {cohError && <div style={{ ...s.errorBox, marginTop: 10 }}>{cohError}</div>}
        {!cohResult && !cohLoading && (
          <div style={{ ...s.emptyBox, padding: '24px 0' }}>
            <GitBranch size={24} style={{ margin: '0 auto 8px', display: 'block', opacity: 0.3 }} />
            <span style={{ fontSize: 13, color: '#9ca3af' }}>
              {t('chart_decomp.hurst.coherence_run')}
            </span>
          </div>
        )}
        {cohResult && (
          <div style={{ marginTop: 16 }}>
            <div style={s.chartTitle}>{t('chart_decomp.hurst.coherence_r2')}</div>
            <ScalogramCanvas power={cohResult.r_squared} frequencies={cohResult.frequencies} coi={cohResult.coi} />
            <ColorBar />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Forecast Tab ──────────────────────────────────────────────────────────────

function ForecastTab({ series, t }) {
  const [method, setMethod]   = useState('har');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [result, setResult]   = useState(null);

  const run = async () => {
    if (!series || series.length < 300) {
      setError(t('chart_decomp.forecast.need_more_data')); return;
    }
    setLoading(true); setError(null); setResult(null);
    // Compute log-RV proxy: log(r²) where r = log-return
    const logR = series.slice(1).map((p, i) => Math.log(p / series[i]));
    const logRV = logR.map(r => Math.log(r * r + 1e-10));
    try {
      let resp;
      if (method === 'har') {
        resp = await chartDecompService.harForecast({ log_rv: logRV });
      } else {
        resp = await chartDecompService.vmdHarForecast({ log_rv: logRV });
      }
      setResult({ method, data: resp.data ?? resp });
    } catch (e) {
      setError(t('chart_decomp.forecast.error', { msg: e.response?.data?.detail ?? e.message }));
    } finally {
      setLoading(false);
    }
  };

  const metricColor = (key, v) => {
    if (key === 'r2') return v > 0.3 ? COLORS.success : v > 0 ? COLORS.warn : COLORS.danger;
    return '#111827';
  };

  return (
    <div>
      <div style={s.card}>
        <div style={s.row}>
          <div style={s.field}>
            <span style={s.label}>{t('chart_decomp.forecast.method_label')}</span>
            <select style={s.select} value={method} onChange={e => setMethod(e.target.value)}>
              <option value="har">{t('chart_decomp.forecast.method_har')}</option>
              <option value="vmd_har">{t('chart_decomp.forecast.method_vmd_har')}</option>
            </select>
          </div>
          <button
            style={s.btn(loading ? '#9ca3af' : COLORS.accent)}
            onClick={run}
            disabled={!series || loading}
          >
            {loading ? <Spinner /> : <TrendingUp size={14} />}
            {loading ? t('chart_decomp.forecast.running') : t('chart_decomp.forecast.run_btn')}
          </button>
        </div>
        {error && <div style={{ ...s.errorBox, marginTop: 10 }}>{error}</div>}
      </div>

      {!result && !loading && (
        <EmptyState text={series ? t('chart_decomp.common.run_first') : t('chart_decomp.input.no_data')} />
      )}

      {result && (() => {
        const d = result.data;
        const m = d.metrics ?? {};

        // Build chart data — show last 200 OOS points for readability
        const n = d.timestamps?.length ?? 0;
        const slice = Math.min(n, 200);
        const chartData = d.timestamps.slice(-slice).map((ts, i) => ({
          t: ts,
          pred: d.predictions[n - slice + i],
          actual: d.actuals[n - slice + i],
        }));

        return (
          <>
            {/* Metrics */}
            <div style={s.card}>
              <div style={s.cardTitle}>{t('chart_decomp.forecast.metrics_title')}</div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {[
                  { key: 'rmse',  label: t('chart_decomp.forecast.rmse_label') },
                  { key: 'mae',   label: t('chart_decomp.forecast.mae_label') },
                  { key: 'r2',    label: t('chart_decomp.forecast.r2_label') },
                  { key: 'qlike', label: t('chart_decomp.forecast.qlike_label') },
                ].map(({ key, label }) => (
                  <MetricCard
                    key={key}
                    label={label}
                    value={m[key] != null ? m[key].toFixed(4) : '—'}
                    color={metricColor(key, m[key])}
                  />
                ))}
              </div>
            </div>

            {/* Forecast chart */}
            <div style={s.card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <span style={s.cardTitle}>{t('chart_decomp.forecast.chart_title')}</span>
                <span style={s.badge()}>{t('chart_decomp.forecast.oos_note')}</span>
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={chartData} margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                  <CartesianGrid stroke={COLORS.grid} strokeDasharray={COLORS.gridDash} />
                  <XAxis dataKey="t" tick={{ fontSize: 10, fontFamily: FONT, fill: COLORS.axis }}
                    label={{ value: 't', position: 'insideBottomRight', offset: 0, fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10, fontFamily: FONT, fill: COLORS.axis }}
                    label={{ value: 'log-RV', angle: -90, position: 'insideLeft', fontSize: 10 }} />
                  <Tooltip
                    formatter={(v, name) => [v.toFixed(4), name === 'pred'
                      ? t('chart_decomp.forecast.predicted_label')
                      : t('chart_decomp.forecast.actual_label')]}
                    contentStyle={{ fontSize: 11, fontFamily: FONT, borderRadius: 6 }}
                  />
                  <Line type="monotone" dataKey="actual" stroke={COLORS.original} strokeWidth={1.5}
                    dot={false} name="actual" isAnimationActive={false} />
                  <Line type="monotone" dataKey="pred" stroke={COLORS.accent} strokeWidth={1.5}
                    strokeDasharray="4 2" dot={false} name="pred" isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', gap: 16, marginTop: 8, justifyContent: 'flex-end' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 20, height: 2, background: COLORS.original }} />
                  <span style={{ fontSize: 11, color: COLORS.axis }}>{t('chart_decomp.forecast.actual_label')}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 20, height: 2, background: COLORS.accent, borderTop: '2px dashed' + COLORS.accent }} />
                  <span style={{ fontSize: 11, color: COLORS.axis }}>{t('chart_decomp.forecast.predicted_label')}</span>
                </div>
              </div>
            </div>
          </>
        );
      })()}
    </div>
  );
}

// ── Pattern Detection Tab (FR-VIZ-1, FR-VIZ-2 — CD-617) ──────────────────────

const PATTERN_COLORS = [
  '#6366f1','#f59e0b','#10b981','#ef4444','#8b5cf6',
  '#06b6d4','#ec4899','#84cc16','#fb923c',
];

function PatternTab({ series, t }) {
  const [kDrop, setKDrop]       = useState(1);
  const [threshold, setThr]     = useState(0.08);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [result, setResult]     = useState(null);

  const run = async () => {
    if (!series) return;
    setLoading(true); setError(null);
    try {
      const data = await chartDecompService.patternPipeline({
        series,
        k_drop: kDrop,
        threshold,
        compute_fpr: false,
      });
      setResult(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!series) return (
    <div style={{ padding: 32, color: COLORS.axis }}>{t('chart_decomp.patterns.no_series')}</div>
  );

  const chartData = result
    ? result.denoised.map((v, i) => ({ i, raw: series[i], denoised: v }))
    : [];

  // Pivot sets
  const highPivots = new Set(result?.swings.filter(s => s.kind === 'H').map(s => s.index) ?? []);
  const lowPivots  = new Set(result?.swings.filter(s => s.kind === 'L').map(s => s.index) ?? []);

  // Detection regions for Panel 3
  const dets = result?.detections ?? [];

  return (
    <div style={{ padding: '0 0 24px' }}>
      {/* Controls */}
      <div style={{ display:'flex', gap:16, alignItems:'flex-end', marginBottom:20,
                    background:COLORS.card, border:`1px solid ${COLORS.border}`,
                    borderRadius:8, padding:'14px 18px' }}>
        <label style={{ fontSize:13 }}>
          {t('chart_decomp.patterns.k_drop_label')}
          <br />
          <select value={kDrop} onChange={e => setKDrop(+e.target.value)}
                  style={{ marginTop:4, padding:'3px 8px', borderRadius:4,
                           border:`1px solid ${COLORS.border}`, fontSize:13 }}>
            {[0,1,2,3,4].map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
        <label style={{ fontSize:13 }}>
          {t('chart_decomp.patterns.threshold_label')}
          <br />
          <input type="number" value={threshold} min={0.01} max={0.5} step={0.01}
                 onChange={e => setThr(+e.target.value)}
                 style={{ marginTop:4, width:70, padding:'3px 8px', borderRadius:4,
                          border:`1px solid ${COLORS.border}`, fontSize:13 }} />
        </label>
        <button onClick={run} disabled={loading}
                style={{ padding:'6px 18px', background:COLORS.accent, color:'#fff',
                         border:'none', borderRadius:6, cursor:'pointer', fontSize:13 }}>
          {loading ? t('chart_decomp.patterns.running') : t('chart_decomp.patterns.run_btn')}
        </button>
        {error && <span style={{ color:COLORS.danger, fontSize:12 }}>
          {t('chart_decomp.patterns.error', { msg: error })}
        </span>}
      </div>

      {result && (<>
        {/* Panel 1 — Raw vs Denoised (FR-VIZ-1 §1) */}
        <h4 style={{ fontSize:13, color:COLORS.axis, margin:'0 0 6px' }}>
          {t('chart_decomp.patterns.panel1_title')}
        </h4>
        <div style={{ background:COLORS.card, border:`1px solid ${COLORS.border}`,
                      borderRadius:8, padding:'12px 4px', marginBottom:16 }}>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray={COLORS.gridDash} stroke={COLORS.grid} />
              <XAxis dataKey="i" tick={{ fontSize:10 }} />
              <YAxis tick={{ fontSize:10 }} width={50} />
              <Tooltip contentStyle={{ fontSize:11 }} />
              <Line dataKey="raw" stroke={COLORS.original} dot={false} strokeWidth={1}
                    name={t('chart_decomp.patterns.raw_label')} />
              <Line dataKey="denoised" stroke={COLORS.accent} dot={false} strokeWidth={1.5}
                    name={t('chart_decomp.patterns.denoised_label')} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Panel 2 — Swing Skeleton (FR-VIZ-1 §2) */}
        <h4 style={{ fontSize:13, color:COLORS.axis, margin:'0 0 6px' }}>
          {t('chart_decomp.patterns.panel2_title')}
          <span style={{ marginLeft:8, fontSize:11, color:COLORS.axis }}>
            ({result.swings.length} pivots)
          </span>
        </h4>
        <div style={{ background:COLORS.card, border:`1px solid ${COLORS.border}`,
                      borderRadius:8, padding:'12px 4px', marginBottom:16 }}>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray={COLORS.gridDash} stroke={COLORS.grid} />
              <XAxis dataKey="i" tick={{ fontSize:10 }} />
              <YAxis tick={{ fontSize:10 }} width={50} />
              <Tooltip contentStyle={{ fontSize:11 }} />
              <Line dataKey="denoised" stroke={COLORS.accent} dot={(props) => {
                const { cx, cy, payload } = props;
                if (highPivots.has(payload.i))
                  return <circle key={payload.i} cx={cx} cy={cy} r={4}
                                 fill={COLORS.danger} stroke="none" />;
                if (lowPivots.has(payload.i))
                  return <circle key={payload.i} cx={cx} cy={cy} r={4}
                                 fill={COLORS.success} stroke="none" />;
                return null;
              }} strokeWidth={1.5} name={t('chart_decomp.patterns.denoised_label')} />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display:'flex', gap:16, padding:'4px 12px', fontSize:11 }}>
            <span><span style={{ color:COLORS.danger }}>●</span> {t('chart_decomp.patterns.high_label')}</span>
            <span><span style={{ color:COLORS.success }}>●</span> {t('chart_decomp.patterns.low_label')}</span>
          </div>
        </div>

        {/* Panel 3 — Detected Patterns (FR-VIZ-1 §3) */}
        <h4 style={{ fontSize:13, color:COLORS.axis, margin:'0 0 6px' }}>
          {t('chart_decomp.patterns.panel3_title')}
          <span style={{ marginLeft:8, fontSize:11, color:COLORS.axis }}>
            ({dets.length} {t('chart_decomp.patterns.no_detections').startsWith('No') ? 'found' : ''})
          </span>
        </h4>
        <div style={{ background:COLORS.card, border:`1px solid ${COLORS.border}`,
                      borderRadius:8, padding:'12px 4px', marginBottom:16 }}>
          {dets.length === 0
            ? <p style={{ padding:'24px 16px', color:COLORS.axis, fontSize:13 }}>
                {t('chart_decomp.patterns.no_detections')}
              </p>
            : <ResponsiveContainer width="100%" height={180}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray={COLORS.gridDash} stroke={COLORS.grid} />
                  <XAxis dataKey="i" tick={{ fontSize:10 }} />
                  <YAxis tick={{ fontSize:10 }} width={50} />
                  <Tooltip contentStyle={{ fontSize:11 }} />
                  {dets.map((d, idx) => (
                    <ReferenceArea key={idx} x1={d.start_index} x2={d.end_index}
                                   fill={PATTERN_COLORS[idx % PATTERN_COLORS.length]}
                                   fillOpacity={d.confirmed ? 0.15 : 0.07}
                                   stroke={PATTERN_COLORS[idx % PATTERN_COLORS.length]}
                                   strokeOpacity={0.4} strokeDasharray={d.confirmed ? 'none' : '4 2'} />
                  ))}
                  <Line dataKey="denoised" stroke={COLORS.original} dot={false} strokeWidth={1.5} />
                </LineChart>
              </ResponsiveContainer>
          }
        </div>

        {/* FR-VIZ-2 — Detection report */}
        <h4 style={{ fontSize:13, color:COLORS.axis, margin:'0 0 6px' }}>
          {t('chart_decomp.patterns.report_title')}
        </h4>
        <div style={{ background:COLORS.card, border:`1px solid ${COLORS.border}`,
                      borderRadius:8, overflow:'auto' }}>
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:12 }}>
            <thead>
              <tr style={{ background:COLORS.bg }}>
                {['col_pattern','col_start','col_end','col_score','col_confirmed','col_null_pct'].map(k => (
                  <th key={k} style={{ padding:'8px 12px', textAlign:'left',
                                       borderBottom:`1px solid ${COLORS.border}`,
                                       color:COLORS.axis, fontWeight:600 }}>
                    {t(`chart_decomp.patterns.${k}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dets.length === 0
                ? <tr><td colSpan={6} style={{ padding:'12px', color:COLORS.axis, textAlign:'center' }}>
                    {t('chart_decomp.patterns.no_detections')}
                  </td></tr>
                : dets.map((d, i) => (
                  <tr key={i} style={{ borderBottom:`1px solid ${COLORS.border}` }}>
                    <td style={{ padding:'7px 12px', fontWeight:500,
                                 color: PATTERN_COLORS[i % PATTERN_COLORS.length] }}>{d.pattern}</td>
                    <td style={{ padding:'7px 12px' }}>{d.start_index}</td>
                    <td style={{ padding:'7px 12px' }}>{d.end_index}</td>
                    <td style={{ padding:'7px 12px' }}>{(d.score * 100).toFixed(0)}%</td>
                    <td style={{ padding:'7px 12px' }}>
                      {d.confirmed
                        ? <span style={{ color:COLORS.success }}>✓</span>
                        : <span style={{ color:COLORS.warn, fontSize:11 }}>Edge?</span>}
                    </td>
                    <td style={{ padding:'7px 12px', color:COLORS.axis }}>
                      {d.null_percentile != null ? `${(d.null_percentile*100).toFixed(0)}%` : '—'}
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      </>)}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const TABS = ['decomp', 'time_freq', 'hurst', 'forecast', 'patterns'];

const TAB_ICONS = {
  decomp:    Activity,
  time_freq: BarChart2,
  hurst:     TrendingUp,
  forecast:  Zap,
  patterns:  GitBranch,
};

export default function ChartDecompPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('decomp');
  const [series, setSeries]       = useState(null);

  return (
    <div style={s.page}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      {/* Header */}
      <div style={s.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Activity size={22} color={COLORS.accent} />
          <h1 style={s.h1}>{t('chart_decomp.page_title')}</h1>
        </div>
        <p style={s.subtitle}>{t('chart_decomp.page_subtitle')}</p>
      </div>

      {/* Input panel (always visible) */}
      <InputPanel onSeriesReady={(s) => setSeries(s)} t={t} />

      {/* Tab bar */}
      <div style={s.tabBar}>
        {TABS.map(tab => {
          const Icon = TAB_ICONS[tab];
          return (
            <button key={tab} style={s.tab(activeTab === tab)} onClick={() => setActiveTab(tab)}>
              <Icon size={13} style={{ verticalAlign: 'middle', marginRight: 4 }} />
              {t(`chart_decomp.tabs.${tab}`)}
            </button>
          );
        })}
      </div>

      {/* Tab panels */}
      {activeTab === 'decomp'    && <DecompTab    series={series} t={t} />}
      {activeTab === 'time_freq' && <TimeFreqTab  series={series} t={t} />}
      {activeTab === 'hurst'     && <HurstTab     series={series} t={t} />}
      {activeTab === 'forecast'  && <ForecastTab  series={series} t={t} />}
      {activeTab === 'patterns'  && <PatternTab   series={series} t={t} />}
    </div>
  );
}
