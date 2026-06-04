// F-054 — BacktestStudio page (Phase F)
// Configure + run backtest / walk-forward; show equity curve, trade ledger, stats.
import React, { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { Play, BarChart2, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import helperService from '../../../services/helperService';

const today = () => new Date().toISOString().split('T')[0];
const oneYearAgo = () => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().split('T')[0];
};

const DEFAULT_CONFIG = {
  ticker: 'VCB',
  startDate: oneYearAgo(),
  endDate: today(),
  initialEquity: 100000,
  riskPerTradePct: 1.0,
  fastMa: 10,
  slowMa: 50,
  breakoutN: 20,
  kDelay: 1,
  slippageBps: 5,
  commission: 10,
  walkForward: false,
  wfWindowDays: 90,
};

const fmt2 = (v) => v != null ? Number(v).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—';
const fmtPct = (v) => v != null ? `${(Number(v) * 100).toFixed(2)}%` : '—';
const fmtPctRaw = (v) => v != null ? `${Number(v).toFixed(2)}%` : '—';

const StatCard = ({ label, value, color }) => (
  <div style={s.statCard}>
    <div style={{ fontSize: 10, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
    <div style={{ fontSize: 18, fontWeight: 800, color: color || '#111827', marginTop: 2 }}>{value}</div>
  </div>
);

const BacktestStudio = () => {
  const { t } = useTranslation();
  const [cfg, setCfg] = useState(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [showLedger, setShowLedger] = useState(false);
  const [showWF, setShowWF] = useState(false);

  const set = (k) => (e) => {
    const v = e.target.type === 'checkbox' ? e.target.checked
      : e.target.type === 'number' ? Number(e.target.value)
      : e.target.value;
    setCfg(p => ({ ...p, [k]: v }));
  };

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    const res = await helperService.runBacktest(cfg);
    if (res?.success) {
      setResult(res.data);
    } else {
      setError(res?.error?.message || t('decision_helper.backtest_studio.failed'));
    }
    setLoading(false);
  };

  const stats = result?.stats;

  return (
    <div style={s.page}>
      {/* ── Config panel ──────────────────────────────────────────────── */}
      <div style={s.panel}>
        <div style={s.panelHeader}>
          <BarChart2 size={16} style={{ color: '#6366f1' }} />
          <span style={{ fontWeight: 700, fontSize: 14 }}>{t('decision_helper.backtest_studio.title')}</span>
        </div>

        <div style={s.configGrid}>
          <Field label={t('decision_helper.backtest_studio.ticker')} value={cfg.ticker} onChange={set('ticker')} type="text" />
          <Field label={t('decision_helper.backtest_studio.start_date')} value={cfg.startDate} onChange={set('startDate')} type="date" />
          <Field label={t('decision_helper.backtest_studio.end_date')} value={cfg.endDate} onChange={set('endDate')} type="date" />
          <Field label={t('decision_helper.backtest_studio.initial_equity')} value={cfg.initialEquity} onChange={set('initialEquity')} type="number" step={10000} />
          <Field label={t('decision_helper.backtest_studio.risk_per_trade')} value={cfg.riskPerTradePct} onChange={set('riskPerTradePct')} type="number" step={0.1} min={0.1} max={10} />
          <Field label={t('decision_helper.backtest_studio.fast_ma')} value={cfg.fastMa} onChange={set('fastMa')} type="number" step={1} min={2} max={50} />
          <Field label={t('decision_helper.backtest_studio.slow_ma')} value={cfg.slowMa} onChange={set('slowMa')} type="number" step={5} min={10} max={200} />
          <Field label={t('decision_helper.backtest_studio.breakout_n')} value={cfg.breakoutN} onChange={set('breakoutN')} type="number" step={1} min={5} max={100} />
          <Field label={t('decision_helper.backtest_studio.k_delay')} value={cfg.kDelay} onChange={set('kDelay')} type="number" step={1} min={1} max={5} />
          <Field label={t('decision_helper.backtest_studio.slippage')} value={cfg.slippageBps} onChange={set('slippageBps')} type="number" step={1} min={0} />
          <Field label={t('decision_helper.backtest_studio.commission')} value={cfg.commission} onChange={set('commission')} type="number" step={1} min={0} />
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
            <label style={{ fontSize: 10, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              {t('decision_helper.backtest_studio.walk_forward')}
            </label>
            <input
              type="checkbox"
              checked={cfg.walkForward}
              onChange={set('walkForward')}
              style={{ marginBottom: 6, cursor: 'pointer', accentColor: '#6366f1' }}
            />
          </div>
          {cfg.walkForward && (
            <Field label={t('decision_helper.backtest_studio.wf_window')} value={cfg.wfWindowDays} onChange={set('wfWindowDays')} type="number" step={30} min={10} max={365} />
          )}
        </div>

        <button onClick={run} disabled={loading} style={s.runBtn}>
          {loading
            ? <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />
            : <Play size={14} />}
          {loading ? t('decision_helper.common.running') : t('decision_helper.backtest_studio.run')}
        </button>

        {error && <div style={s.error}>{error}</div>}
      </div>

      {/* ── Results ────────────────────────────────────────────────────── */}
      {result && stats && (
        <>
          {/* Stats row */}
          <div style={s.statsRow}>
            <StatCard label={t('decision_helper.backtest_studio.trades')} value={stats.num_trades} />
            <StatCard label={t('decision_helper.backtest_studio.win_rate')} value={fmtPct(stats.win_rate)} color={stats.win_rate >= 0.5 ? '#10b981' : '#ef4444'} />
            <StatCard label={t('decision_helper.backtest_studio.net_pnl')} value={`$${fmt2(stats.total_net_pnl)}`} color={stats.total_net_pnl >= 0 ? '#10b981' : '#ef4444'} />
            <StatCard label={t('decision_helper.backtest_studio.max_drawdown')} value={fmtPctRaw(stats.max_drawdown_pct * 100)} color={stats.max_drawdown_pct > 0.2 ? '#ef4444' : '#f59e0b'} />
            <StatCard label={t('decision_helper.backtest_studio.expectancy')} value={`$${fmt2(stats.expectancy)}`} color={stats.expectancy >= 0 ? '#10b981' : '#ef4444'} />
            {stats.sharpe_ratio != null && <StatCard label={t('decision_helper.backtest_studio.sharpe')} value={stats.sharpe_ratio.toFixed(2)} color={stats.sharpe_ratio >= 1 ? '#10b981' : '#9ca3af'} />}
            {stats.profit_factor != null && <StatCard label={t('decision_helper.backtest_studio.profit_factor')} value={stats.profit_factor.toFixed(2)} color={stats.profit_factor >= 1.5 ? '#10b981' : '#9ca3af'} />}
            <StatCard label={t('decision_helper.backtest_studio.latency')} value={`${result.latency_ms}ms`} />
          </div>

          {/* Equity curve */}
          {result.equity_curve?.length > 0 && (
            <div style={s.chartPanel}>
              <div style={s.chartTitle}>{t('decision_helper.backtest_studio.equity_curve', { ticker: result.ticker })}</div>
              <ResponsiveContainer width="100%" height={460}>
                <LineChart data={result.equity_curve} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#6b7280', fontSize: 10 }}
                    tickFormatter={(d) => d?.slice(5)}  // MM-DD
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fill: '#6b7280', fontSize: 10 }}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    width={52}
                  />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 6, fontSize: 12 }}
                    formatter={(v) => [`$${fmt2(v)}`, t('decision_helper.backtest_studio.equity_label')]}
                    labelStyle={{ color: '#6b7280' }}
                  />
                  <ReferenceLine
                    y={cfg.initialEquity}
                    stroke="#9ca3af"
                    strokeDasharray="4 4"
                    label={{ value: t('decision_helper.backtest_studio.start_label'), fill: '#9ca3af', fontSize: 10 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="equity"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: '#6366f1' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Walk-forward summary */}
          {result.walk_forward_windows?.length > 0 && (
            <div style={s.section}>
              <button onClick={() => setShowWF(p => !p)} style={s.collapseBtn}>
                {t('decision_helper.backtest_studio.wf_windows', { count: result.walk_forward_windows.length })}
                {showWF ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {showWF && (
                <>
                  {result.walk_forward_aggregate && (
                    <div style={s.wfAgg}>
                      {Object.entries(result.walk_forward_aggregate).map(([k, v]) => (
                        <span key={k} style={s.wfAggItem}>
                          <span style={{ color: '#9ca3af' }}>{k.replace(/_/g, ' ')}</span>{' '}
                          <strong>{typeof v === 'number' ? v.toFixed(3) : v}</strong>
                        </span>
                      ))}
                    </div>
                  )}
                  <div style={{ overflowX: 'auto', marginTop: 8 }}>
                    <table style={s.table}>
                      <thead>
                        <tr>
                          {[
                            t('decision_helper.backtest_studio.col_num'),
                            t('decision_helper.backtest_studio.col_start'),
                            t('decision_helper.backtest_studio.col_end'),
                            t('decision_helper.backtest_studio.col_trades'),
                            t('decision_helper.backtest_studio.col_win_pct'),
                            t('decision_helper.backtest_studio.col_net_pnl'),
                            t('decision_helper.backtest_studio.col_max_dd'),
                            t('decision_helper.backtest_studio.col_expectancy'),
                          ].map(h => (
                            <th key={h} style={s.th}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.walk_forward_windows.map(w => (
                          <tr key={w.window_index} style={s.tr}>
                            <td style={s.td}>{w.window_index + 1}</td>
                            <td style={s.td}>{w.start_date}</td>
                            <td style={s.td}>{w.end_date}</td>
                            <td style={s.td}>{w.stats.num_trades}</td>
                            <td style={{ ...s.td, color: w.stats.win_rate >= 0.5 ? '#10b981' : '#ef4444' }}>
                              {fmtPct(w.stats.win_rate)}
                            </td>
                            <td style={{ ...s.td, color: w.stats.total_net_pnl >= 0 ? '#10b981' : '#ef4444' }}>
                              ${fmt2(w.stats.total_net_pnl)}
                            </td>
                            <td style={{ ...s.td, color: '#f59e0b' }}>{fmtPctRaw(w.stats.max_drawdown_pct * 100)}</td>
                            <td style={{ ...s.td, color: w.stats.expectancy >= 0 ? '#10b981' : '#ef4444' }}>
                              ${fmt2(w.stats.expectancy)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Trade ledger */}
          {result.trade_ledger?.length > 0 && (
            <div style={s.section}>
              <button onClick={() => setShowLedger(p => !p)} style={s.collapseBtn}>
                {t('decision_helper.backtest_studio.ledger', { count: result.trade_ledger.length })}
                {showLedger ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {showLedger && (
                <div style={{ overflowX: 'auto', marginTop: 8 }}>
                  <table style={s.table}>
                    <thead>
                      <tr>
                        {[
                          t('decision_helper.backtest_studio.col_dir'),
                          t('decision_helper.backtest_studio.col_entry_date'),
                          t('decision_helper.backtest_studio.col_entry_price'),
                          t('decision_helper.backtest_studio.col_exit_date'),
                          t('decision_helper.backtest_studio.col_exit_price'),
                          t('decision_helper.backtest_studio.col_shares'),
                          t('decision_helper.backtest_studio.col_gross_pnl'),
                          t('decision_helper.backtest_studio.col_net_pnl'),
                          t('decision_helper.backtest_studio.col_exit_reason'),
                        ].map(h => (
                          <th key={h} style={s.th}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.trade_ledger.map((t, i) => (
                        <tr key={i} style={s.tr}>
                          <td style={{ ...s.td, color: t.direction === 'LONG' ? '#10b981' : '#ef4444', fontWeight: 700 }}>{t.direction}</td>
                          <td style={s.td}>{t.entry_date}</td>
                          <td style={s.td}>{fmt2(t.entry_price)}</td>
                          <td style={s.td}>{t.exit_date || '—'}</td>
                          <td style={s.td}>{fmt2(t.exit_price)}</td>
                          <td style={s.td}>{t.shares}</td>
                          <td style={{ ...s.td, color: (t.gross_pnl || 0) >= 0 ? '#10b981' : '#ef4444' }}>{fmt2(t.gross_pnl)}</td>
                          <td style={{ ...s.td, color: (t.net_pnl || 0) >= 0 ? '#10b981' : '#ef4444', fontWeight: 600 }}>{fmt2(t.net_pnl)}</td>
                          <td style={{ ...s.td, fontSize: 11, color: '#9ca3af' }}>{t.exit_reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

const Field = ({ label, value, onChange, type = 'text', step, min, max }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
    <label style={{ fontSize: 10, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</label>
    <input
      type={type} value={value} onChange={onChange}
      step={step} min={min} max={max}
      style={{
        background: '#ffffff', border: '1px solid #d1d5db', borderRadius: 5,
        padding: '6px 8px', color: '#111827', fontSize: 13, outline: 'none',
      }}
    />
  </div>
);

const s = {
  page: { padding: 20, color: '#111827', maxWidth: 1200, margin: '0 auto' },
  panel: {
    background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, marginBottom: 16,
    boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
  },
  panelHeader: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14, fontSize: 14 },
  configGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 10, marginBottom: 14,
  },
  runBtn: {
    background: '#6366f1', border: 'none', borderRadius: 7,
    padding: '9px 20px', color: '#fff', fontWeight: 700, fontSize: 13,
    cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 7,
  },
  error: { color: '#ef4444', fontSize: 13, marginTop: 8 },
  statsRow: {
    display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16,
  },
  statCard: {
    background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 8,
    padding: '10px 14px', minWidth: 100, boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
  },
  chartPanel: {
    background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 10,
    padding: '14px 10px', marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
  },
  chartTitle: { fontSize: 13, fontWeight: 700, color: '#111827', marginBottom: 10, paddingLeft: 4 },
  section: {
    background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 10,
    padding: 14, marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
  },
  collapseBtn: {
    background: 'none', border: 'none', color: '#374151', fontWeight: 700, fontSize: 13,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, padding: 0,
  },
  wfAgg: { display: 'flex', flexWrap: 'wrap', gap: 12, margin: '10px 0', fontSize: 12 },
  wfAggItem: { color: '#374151' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: {
    background: '#f9fafb', padding: '8px 10px', textAlign: 'left',
    color: '#6b7280', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5,
    borderBottom: '1px solid #e5e7eb', whiteSpace: 'nowrap',
  },
  tr: { borderBottom: '1px solid #f3f4f6' },
  td: { padding: '8px 10px', color: '#374151', verticalAlign: 'middle', whiteSpace: 'nowrap' },
};

export default BacktestStudio;
