// F-131..F-133 — AnalyticsPage: decision-run performance analytics
import React, { useState, useEffect, useCallback } from 'react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { BarChart2, RefreshCw, TrendingUp, Zap, CheckCircle, Clock } from 'lucide-react';
import helperService from '../../../services/helperService';

// ── palette ──────────────────────────────────────────────────────────────────

const ACTION_COLORS = {
  BUY: '#10b981', SELL_SHORT: '#f59e0b', SELL: '#ef4444',
  COVER: '#3b82f6', REVERSE: '#8b5cf6', HOLD: '#6b7280', WAIT: '#4b5563',
};
const REGIME_COLORS = {
  TREND_UP: '#10b981', TREND_DOWN: '#ef4444', RANGE: '#f59e0b', UNDEFINED: '#6b7280',
};

const DAY_OPTIONS = [30, 60, 90, 180, 365];

const fmt1 = (v) => v != null ? Number(v).toFixed(1) : '—';
const fmtPct = (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—';

// ── Summary cards ─────────────────────────────────────────────────────────────

const StatCard = ({ label, value, sub, color, icon: Icon }) => (
  <div style={styles.statCard}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 8 }}>
      {Icon && <Icon size={14} color={color || '#a78bfa'} />}
      <span style={{ fontSize: 10, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</span>
    </div>
    <div style={{ fontSize: 22, fontWeight: 800, color: color || '#f9fafb' }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: '#6b7280', marginTop: 3 }}>{sub}</div>}
  </div>
);

// ── Signal breakdown table ────────────────────────────────────────────────────

const SignalTable = ({ rows }) => {
  if (!rows || rows.length === 0) return (
    <div style={styles.emptyCell}>No signal data yet.</div>
  );
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={styles.table}>
        <thead>
          <tr>
            {['Signal', 'Fires', 'Confirmed', 'Confirm %', 'Avg Conf'].map(h => (
              <th key={h} style={styles.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.signal_kind} style={{ background: i % 2 === 0 ? '#111827' : 'transparent' }}>
              <td style={{ ...styles.td, fontWeight: 700, color: '#f9fafb' }}>{r.signal_kind}</td>
              <td style={styles.td}>{r.fire_count}</td>
              <td style={styles.td}>{r.confirmed_count}</td>
              <td style={{ ...styles.td, color: r.confirmation_rate >= 0.5 ? '#10b981' : '#f59e0b' }}>
                {fmtPct(r.confirmation_rate)}
              </td>
              <td style={{ ...styles.td, color: '#a78bfa' }}>{fmtPct(r.avg_confidence)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// ── Top tickers table ─────────────────────────────────────────────────────────

const TopTickersTable = ({ rows }) => {
  if (!rows || rows.length === 0) return (
    <div style={styles.emptyCell}>No ticker data yet.</div>
  );
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={styles.table}>
        <thead>
          <tr>
            {['Ticker', 'Decisions', 'BUY', 'SELL SHORT'].map(h => (
              <th key={h} style={styles.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.ticker} style={{ background: i % 2 === 0 ? '#111827' : 'transparent' }}>
              <td style={{ ...styles.td, fontWeight: 700, color: '#f9fafb' }}>{r.ticker}</td>
              <td style={styles.td}>{r.decision_count}</td>
              <td style={{ ...styles.td, color: '#10b981', fontWeight: 600 }}>{r.buy_count || '—'}</td>
              <td style={{ ...styles.td, color: '#f59e0b', fontWeight: 600 }}>{r.sell_short_count || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// ── Custom tooltip ────────────────────────────────────────────────────────────

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: '#9ca3af', marginBottom: 4 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color || '#f9fafb' }}>
          {p.name}: <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

const AnalyticsPage = () => {
  const [days, setDays] = useState(90);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (d) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await helperService.getAnalytics(d);
      setData(resp);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(days); }, [days, load]);

  const handleDays = (d) => { setDays(d); };

  // Derive top signal + regime for summary cards
  const topSignal = data?.signal_breakdown?.[0]?.signal_kind ?? '—';
  const topRegime = data?.regime_breakdown?.[0]?.regime ?? '—';
  const actionablePct = data?.total_decisions
    ? ((data.actionable_count / data.total_decisions) * 100).toFixed(1)
    : '0';

  return (
    <div style={styles.page}>
      {/* ── Header ── */}
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BarChart2 size={18} color="#a78bfa" />
          <span style={{ fontWeight: 700, fontSize: 16, color: '#f9fafb' }}>Performance Analytics</span>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {DAY_OPTIONS.map(d => (
            <button key={d} onClick={() => handleDays(d)} style={{
              ...styles.dayBtn,
              background: days === d ? '#7c3aed' : '#1f2937',
              color: days === d ? '#fff' : '#9ca3af',
              borderColor: days === d ? '#7c3aed' : '#374151',
            }}>
              {d}d
            </button>
          ))}
          <button onClick={() => load(days)} disabled={loading} style={styles.refreshBtn}>
            <RefreshCw size={14} style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
          </button>
        </div>
      </div>

      {error && <div style={styles.errorBanner}>{error}</div>}

      {loading && !data && (
        <div style={styles.loadingBox}>
          <RefreshCw size={24} color="#a78bfa" style={{ animation: 'spin 1s linear infinite' }} />
          <span style={{ color: '#9ca3af', marginTop: 10 }}>Loading analytics…</span>
        </div>
      )}

      {data && (
        <>
          {/* ── Summary cards ── */}
          <div style={styles.statsRow}>
            <StatCard label="Total Decisions" value={data.total_decisions} icon={Zap}
              sub={`last ${data.days} days`} />
            <StatCard label="Actionable" value={`${actionablePct}%`}
              color={parseFloat(actionablePct) >= 20 ? '#10b981' : '#f59e0b'}
              icon={TrendingUp}
              sub={`${data.actionable_count} BUY / SELL SHORT`} />
            <StatCard label="Top Signal" value={topSignal} icon={CheckCircle} color="#a78bfa"
              sub={`${fmtPct(data.signal_breakdown?.[0]?.confirmation_rate)} confirm rate`} />
            <StatCard label="Top Regime" value={topRegime} icon={Clock}
              color={REGIME_COLORS[topRegime] || '#6b7280'}
              sub={`${data.regime_breakdown?.[0]?.total ?? 0} decisions`} />
          </div>

          {/* ── Daily actionable trend ── */}
          {data.daily_actionable?.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Daily Actionable Signals (BUY + SELL SHORT)</div>
              <ResponsiveContainer width="100%" height={180}>
                <AreaChart data={data.daily_actionable} margin={{ top: 6, right: 16, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }}
                    tickFormatter={d => d?.slice(5)} interval="preserveStartEnd" />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} width={28} allowDecimals={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Area type="monotone" dataKey="count" name="Signals"
                    stroke="#a78bfa" strokeWidth={2} fill="url(#grad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ── Two-column: action breakdown + confidence histogram ── */}
          <div style={styles.twoCol}>
            {/* Action breakdown */}
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Action Distribution</div>
              {data.action_breakdown?.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={data.action_breakdown} layout="vertical"
                    margin={{ top: 4, right: 20, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                    <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} />
                    <YAxis type="category" dataKey="action" width={72}
                      tick={{ fill: '#d1d5db', fontSize: 11, fontWeight: 600 }} />
                    <Tooltip content={<ChartTooltip />} />
                    <Bar dataKey="count" name="Decisions" radius={[0, 4, 4, 0]}>
                      {data.action_breakdown.map(entry => (
                        <Cell key={entry.action}
                          fill={ACTION_COLORS[entry.action] || '#6b7280'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : <div style={styles.emptyCell}>No data yet.</div>}
            </div>

            {/* Confidence histogram */}
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Confidence Distribution</div>
              {data.confidence_histogram?.some(b => b.count > 0) ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={data.confidence_histogram}
                    margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="bucket" tick={{ fill: '#6b7280', fontSize: 9 }}
                      angle={-30} textAnchor="end" height={40} />
                    <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} width={28} allowDecimals={false} />
                    <Tooltip content={<ChartTooltip />} />
                    <Bar dataKey="count" name="Decisions" fill="#7c3aed" radius={[3, 3, 0, 0]}>
                      {data.confidence_histogram.map((b, i) => {
                        const pct = parseInt(b.bucket);
                        const c = pct >= 70 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#6b7280';
                        return <Cell key={b.bucket} fill={c} />;
                      })}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : <div style={styles.emptyCell}>No data yet.</div>}
            </div>
          </div>

          {/* ── Regime breakdown ── */}
          {data.regime_breakdown?.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Regime Breakdown</div>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={data.regime_breakdown}
                  margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="regime" tick={{ fill: '#d1d5db', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} width={32} allowDecimals={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="buy_count" name="BUY" fill="#10b981" radius={[3, 3, 0, 0]} stackId="a" />
                  <Bar dataKey="sell_short_count" name="SELL SHORT" fill="#f59e0b" stackId="a" />
                  <Bar dataKey="hold_wait_count" name="HOLD/WAIT" fill="#374151" stackId="a" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ── Two-column: signal breakdown + top tickers ── */}
          <div style={styles.twoCol}>
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Signal Breakdown</div>
              <SignalTable rows={data.signal_breakdown} />
            </div>
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Top Tickers</div>
              <TopTickersTable rows={data.top_tickers} />
            </div>
          </div>

          <div style={{ fontSize: 11, color: '#4b5563', textAlign: 'right', marginTop: 4 }}>
            Computed at {new Date(data.computed_at).toLocaleString()} · {data.total_decisions} decisions over {data.days} days
          </div>
        </>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

const styles = {
  page: { padding: 20, maxWidth: 1100, margin: '0 auto', color: '#f9fafb' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 },
  dayBtn: {
    padding: '5px 10px', borderRadius: 6, border: '1px solid', fontSize: 12, fontWeight: 600,
    cursor: 'pointer', transition: 'all 0.15s',
  },
  refreshBtn: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 6,
    padding: '6px 8px', color: '#9ca3af', cursor: 'pointer', display: 'flex',
  },
  errorBanner: {
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 8, padding: '10px 14px', color: '#fca5a5', fontSize: 13, marginBottom: 12,
  },
  loadingBox: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', minHeight: 200,
  },
  statsRow: { display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 16 },
  statCard: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 10,
    padding: '14px 18px', flex: '1 1 180px',
  },
  section: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 10,
    padding: '14px 16px', marginBottom: 14,
  },
  sectionTitle: { fontSize: 12, fontWeight: 700, color: '#d1d5db', marginBottom: 12, letterSpacing: 0.3 },
  twoCol: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 0 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: {
    padding: '7px 10px', textAlign: 'left', color: '#9ca3af',
    fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5,
    borderBottom: '1px solid #374151', whiteSpace: 'nowrap',
  },
  td: { padding: '8px 10px', color: '#d1d5db', verticalAlign: 'middle' },
  emptyCell: { color: '#6b7280', fontSize: 12, padding: '12px 0' },
};

export default AnalyticsPage;
