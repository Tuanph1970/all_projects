// Event-Reaction viewer — price reaction to the SURPRISE of discrete events.
// Measures one event (surprise + market-model abnormal returns + Lee-Mykland jump),
// accumulates measured events into a report table, then runs the cross-sectional
// exposure regression (CAR ~ surprise) across them.
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity, Zap, TrendingUp, BarChart2, Play, Trash2 } from 'lucide-react';
import eventReactionService from '../../../services/eventReactionService';

// ── Palette & theme (mirrors ChartDecomp) ────────────────────────────────────
const COLORS = {
  bg: '#f9fafb', card: '#ffffff', border: '#e5e7eb', grid: '#e5e7eb',
  text: '#111827', muted: '#6b7280', accent: '#6366f1', accentLight: '#eef2ff',
  success: '#10b981', warn: '#f59e0b', danger: '#ef4444', blue: '#3b82f6',
};
const FONT = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";

// httpClient returns { success, data } | { success:false, error } and never throws.
function unwrap(resp) {
  if (!resp || !resp.success) {
    const err = resp?.error;
    throw new Error(err?.data?.detail ?? err?.message ?? 'Request failed');
  }
  return resp.data;
}

const fmt = (x, d = 3) => (x === null || x === undefined || Number.isNaN(x) ? '—' : Number(x).toFixed(d));
const pct = (x, d = 3) => (x === null || x === undefined || Number.isNaN(x) ? '—' : `${(Number(x) * 100).toFixed(d)}%`);

const s = {
  page: { background: COLORS.bg, minHeight: '100vh', padding: '10px 14px', fontFamily: FONT, color: COLORS.text },
  h1: { fontSize: 18, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 8 },
  sub: { fontSize: 12, color: COLORS.muted, marginTop: 2 },
  card: { background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 10, padding: 14, marginTop: 12 },
  cardTitle: { fontSize: 13, fontWeight: 700, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10 },
  field: { display: 'flex', flexDirection: 'column', gap: 4 },
  label: { fontSize: 11, color: COLORS.muted, fontWeight: 600 },
  input: { padding: '7px 9px', border: `1px solid ${COLORS.border}`, borderRadius: 7, fontSize: 13, fontFamily: FONT },
  btn: (disabled) => ({
    padding: '8px 14px', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600,
    background: disabled ? '#c7d2fe' : COLORS.accent, color: '#fff',
    cursor: disabled ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6,
  }),
  btnGhost: { padding: '7px 12px', border: `1px solid ${COLORS.border}`, borderRadius: 7, fontSize: 12,
    background: '#fff', color: COLORS.muted, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 },
  err: { background: '#fef2f2', border: `1px solid ${COLORS.danger}`, color: COLORS.danger, borderRadius: 8, padding: '8px 12px', fontSize: 12, marginTop: 10 },
  statGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 10 },
  stat: { background: COLORS.bg, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: '8px 10px' },
  statLabel: { fontSize: 10, color: COLORS.muted, fontWeight: 600, textTransform: 'uppercase' },
  statValue: { fontSize: 16, fontWeight: 700, marginTop: 2 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: { textAlign: 'left', padding: '7px 8px', borderBottom: `2px solid ${COLORS.border}`, color: COLORS.muted, fontWeight: 700 },
  td: { padding: '7px 8px', borderBottom: `1px solid ${COLORS.grid}` },
  badge: (c) => ({ display: 'inline-block', padding: '1px 8px', borderRadius: 10, fontSize: 11, fontWeight: 700, color: '#fff', background: c }),
};

function Stat({ label, value, color }) {
  return (
    <div style={s.stat}>
      <div style={s.statLabel}>{label}</div>
      <div style={{ ...s.statValue, color: color || COLORS.text }}>{value}</div>
    </div>
  );
}

export default function EventReactionPage() {
  const { t } = useTranslation();

  const [form, setForm] = useState({
    symbol: 'FPT', market_symbol: 'VNINDEX', kind: 'rate_decision',
    date: '2023-06-01', actual: '0.50', consensus: '0.25',
  });
  const [computeNull, setComputeNull] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [latest, setLatest] = useState(null);
  const [rows, setRows] = useState([]);

  const [cluster, setCluster] = useState('event_date');
  const [expLoading, setExpLoading] = useState(false);
  const [exposure, setExposure] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function measure() {
    setLoading(true); setError('');
    try {
      const ts = `${form.date}T00:00:00Z`;
      const body = {
        symbol: form.symbol.trim().toUpperCase(),
        market_symbol: form.market_symbol.trim().toUpperCase(),
        method: 'consensus',
        jump_n_null: computeNull ? 200 : 0,
        event: {
          event_id: `${form.symbol}-${form.date}-${rows.length + 1}`,
          ts_utc: ts,
          kind: form.kind.trim() || 'event',
          actual: parseFloat(form.actual),
          consensus: parseFloat(form.consensus),
        },
      };
      const data = unwrap(await eventReactionService.measure(body));
      setLatest({ ...data, symbol: body.symbol, date: form.date, kind: body.event.kind });
      setRows((r) => [
        ...r,
        {
          asset: body.symbol, event_date: ts, date: form.date, kind: body.event.kind,
          surprise: data.surprise.s, sign: data.surprise.sign,
          car: data.abnormal.car, is_jump: data.jump.is_jump, statistic: data.jump.statistic,
        },
      ]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function runExposure() {
    setExpLoading(true); setError('');
    try {
      const payloadRows = rows.map((r) => ({
        asset: r.asset, event_date: r.event_date, surprise: r.surprise, car: r.car,
      }));
      const data = unwrap(await eventReactionService.crossSection({ rows: payloadRows, cluster }));
      setExposure(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setExpLoading(false);
    }
  }

  const canExpose = rows.length >= 3;

  return (
    <div style={s.page}>
      <div>
        <h1 style={s.h1}><Activity size={20} color={COLORS.accent} /> {t('event_reaction.title')}</h1>
        <div style={s.sub}>{t('event_reaction.subtitle')}</div>
      </div>

      {/* Input */}
      <div style={s.card}>
        <div style={s.cardTitle}><Zap size={15} color={COLORS.accent} /> {t('event_reaction.measure_title')}</div>
        <div style={s.grid}>
          <div style={s.field}><span style={s.label}>{t('event_reaction.symbol')}</span>
            <input style={s.input} value={form.symbol} onChange={set('symbol')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.market')}</span>
            <input style={s.input} value={form.market_symbol} onChange={set('market_symbol')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.kind')}</span>
            <input style={s.input} value={form.kind} onChange={set('kind')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.date')}</span>
            <input type="date" style={s.input} value={form.date} onChange={set('date')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.actual')}</span>
            <input type="number" step="0.01" style={s.input} value={form.actual} onChange={set('actual')} /></div>
          <div style={s.field}><span style={s.label}>{t('event_reaction.consensus')}</span>
            <input type="number" step="0.01" style={s.input} value={form.consensus} onChange={set('consensus')} /></div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 12, flexWrap: 'wrap' }}>
          <button style={s.btn(loading)} onClick={measure} disabled={loading}>
            <Play size={14} /> {loading ? t('event_reaction.running') : t('event_reaction.measure')}
          </button>
          <label style={{ fontSize: 12, color: COLORS.muted, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={computeNull} onChange={(e) => setComputeNull(e.target.checked)} />
            {t('event_reaction.compute_null')}
          </label>
          <span style={{ fontSize: 11, color: COLORS.muted }}>{t('event_reaction.method_note')}</span>
        </div>
        {error && <div style={s.err}>{error}</div>}
      </div>

      {/* Latest measurement detail */}
      {latest && (
        <div style={s.card}>
          <div style={s.cardTitle}><TrendingUp size={15} color={COLORS.blue} />
            {t('event_reaction.latest')}: {latest.symbol} · {latest.date}</div>
          <div style={s.statGrid}>
            <Stat label={t('event_reaction.surprise_std')} value={fmt(latest.surprise.s, 2)}
              color={latest.surprise.sign > 0 ? COLORS.success : latest.surprise.sign < 0 ? COLORS.danger : COLORS.muted} />
            <Stat label={t('event_reaction.surprise_raw')} value={fmt(latest.surprise.s_raw)} />
            <Stat label={t('event_reaction.expected')} value={fmt(latest.surprise.expected)} />
            <Stat label={t('event_reaction.car')} value={pct(latest.abnormal.car)}
              color={latest.abnormal.car >= 0 ? COLORS.success : COLORS.danger} />
            <Stat label={t('event_reaction.beta')} value={fmt(latest.abnormal.beta, 2)} />
            <Stat label={t('event_reaction.sigma_ar')} value={pct(latest.abnormal.sigma_ar)} />
            <Stat label={t('event_reaction.jump')} value={latest.jump.is_jump ? t('event_reaction.yes') : t('event_reaction.no')}
              color={latest.jump.is_jump ? COLORS.warn : COLORS.muted} />
            <Stat label={t('event_reaction.statistic')} value={fmt(latest.jump.statistic, 2)} />
            {computeNull && <Stat label={t('event_reaction.null_fpr')}
              value={latest.jump.null_fpr === null ? '—' : pct(latest.jump.null_fpr, 1)} />}
          </div>
        </div>
      )}

      {/* Report table */}
      <div style={s.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={s.cardTitle}><BarChart2 size={15} color={COLORS.accent} /> {t('event_reaction.report')} ({rows.length})</div>
          {rows.length > 0 && (
            <button style={s.btnGhost} onClick={() => { setRows([]); setExposure(null); }}>
              <Trash2 size={13} /> {t('event_reaction.clear')}
            </button>
          )}
        </div>
        {rows.length === 0 ? (
          <div style={{ fontSize: 12, color: COLORS.muted, padding: '8px 0' }}>{t('event_reaction.no_rows')}</div>
        ) : (
          <table style={s.table}>
            <thead><tr>
              {['symbol', 'date', 'kind', 'surprise_std', 'car', 'jump', 'statistic'].map((c) => (
                <th key={c} style={s.th}>{t(`event_reaction.col_${c}`)}</th>
              ))}
            </tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td style={{ ...s.td, fontWeight: 600 }}>{r.asset}</td>
                  <td style={s.td}>{r.date}</td>
                  <td style={s.td}>{r.kind}</td>
                  <td style={{ ...s.td, color: r.sign > 0 ? COLORS.success : r.sign < 0 ? COLORS.danger : COLORS.muted, fontWeight: 600 }}>{fmt(r.surprise, 2)}</td>
                  <td style={{ ...s.td, color: r.car >= 0 ? COLORS.success : COLORS.danger }}>{pct(r.car)}</td>
                  <td style={s.td}>{r.is_jump ? <span style={s.badge(COLORS.warn)}>{t('event_reaction.yes')}</span> : <span style={{ color: COLORS.muted }}>{t('event_reaction.no')}</span>}</td>
                  <td style={s.td}>{fmt(r.statistic, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Cross-sectional exposure */}
      <div style={s.card}>
        <div style={s.cardTitle}><TrendingUp size={15} color={COLORS.success} /> {t('event_reaction.exposure_title')}</div>
        <div style={{ fontSize: 12, color: COLORS.muted, marginBottom: 10 }}>{t('event_reaction.exposure_hint')}</div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
          <div style={s.field}><span style={s.label}>{t('event_reaction.cluster')}</span>
            <select style={s.input} value={cluster} onChange={(e) => setCluster(e.target.value)}>
              <option value="event_date">{t('event_reaction.cluster_event_date')}</option>
              <option value="portfolio">{t('event_reaction.cluster_portfolio')}</option>
              <option value="iid">{t('event_reaction.cluster_iid')}</option>
            </select>
          </div>
          <button style={s.btn(!canExpose || expLoading)} onClick={runExposure} disabled={!canExpose || expLoading}>
            <Play size={14} /> {expLoading ? t('event_reaction.running') : t('event_reaction.run_exposure')}
          </button>
          {!canExpose && <span style={{ fontSize: 11, color: COLORS.muted }}>{t('event_reaction.need_three')}</span>}
        </div>
        {exposure && (
          <div style={{ ...s.statGrid, marginTop: 12 }}>
            <Stat label={t('event_reaction.gamma1')} value={fmt(exposure.gamma1, 4)} color={COLORS.accent} />
            <Stat label={t('event_reaction.se')} value={fmt(exposure.se_gamma1, 4)} />
            <Stat label="t" value={exposure.se_gamma1 ? fmt(exposure.gamma1 / exposure.se_gamma1, 2) : '—'} />
            <Stat label={t('event_reaction.gamma0')} value={fmt(exposure.gamma0, 4)} />
            <Stat label={t('event_reaction.r_squared')} value={fmt(exposure.r_squared, 3)} />
            <Stat label={t('event_reaction.n_events')} value={exposure.n_event_dates} />
          </div>
        )}
      </div>
    </div>
  );
}
