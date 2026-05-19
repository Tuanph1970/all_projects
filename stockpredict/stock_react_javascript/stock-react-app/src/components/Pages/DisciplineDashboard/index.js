// F-064 — DisciplineDashboard (Phase G)
// Schwager Ch 16-17: streak tracker, drawdown alert, rule-advisory panel
import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert, TrendingDown, CheckCircle, XCircle,
  AlertTriangle, Info, RefreshCw, BookOpen,
} from 'lucide-react';
import helperService from '../../../services/helperService';

// ── helpers ──────────────────────────────────────────────────────────────────

const SEVERITY_META = {
  BLOCK:   { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', Icon: XCircle },
  WARNING: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', Icon: AlertTriangle },
  INFO:    { color: '#6b7280', bg: 'rgba(107,114,128,0.10)', Icon: Info },
};

const pct = (v) => v != null ? `${Number(v).toFixed(1)}%` : '—';

// ── sub-components ────────────────────────────────────────────────────────────

const StatCard = ({ label, value, sub, color = '#f9fafb', warn = false }) => (
  <div style={{ ...s.statCard, borderColor: warn ? '#f59e0b44' : '#37415144' }}>
    <div style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 800, color: warn ? '#f59e0b' : color, lineHeight: 1.2 }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>{sub}</div>}
  </div>
);

const ViolationBadge = ({ v }) => {
  const meta = SEVERITY_META[v.severity] || SEVERITY_META.INFO;
  const Icon = meta.Icon;
  return (
    <div style={{ ...s.violationRow, background: meta.bg, borderColor: meta.color + '44' }}>
      <Icon size={14} style={{ color: meta.color, flexShrink: 0 }} />
      <div>
        <span style={{ color: meta.color, fontWeight: 700, fontSize: 12, marginRight: 8 }}>
          [{v.rule_id}] {v.severity}
        </span>
        <span style={{ color: '#d1d5db', fontSize: 12 }}>{v.message}</span>
      </div>
    </div>
  );
};

const RuleRow = ({ rule }) => {
  const meta = rule.triggered
    ? (SEVERITY_META[rule.severity] || SEVERITY_META.INFO)
    : { color: '#4b5563', bg: 'transparent', Icon: CheckCircle };
  const Icon = rule.triggered ? (SEVERITY_META[rule.severity]?.Icon || Info) : CheckCircle;
  return (
    <div style={{
      display: 'flex', gap: 10, alignItems: 'flex-start',
      padding: '8px 0', borderBottom: '1px solid #1f2937',
      opacity: rule.triggered ? 1 : 0.6,
    }}>
      <Icon size={14} style={{ color: rule.triggered ? meta.color : '#374151', marginTop: 2, flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 600, fontSize: 12, color: rule.triggered ? meta.color : '#9ca3af' }}>
            {rule.rule_id}
          </span>
          <span style={{ fontSize: 11, color: '#6b7280' }}>{rule.chapter}</span>
        </div>
        <div style={{ fontSize: 12, color: rule.triggered ? '#f9fafb' : '#6b7280', marginTop: 2 }}>
          {rule.rule_text}
        </div>
        {rule.triggered && rule.detail && (
          <div style={{ fontSize: 11, color: meta.color, marginTop: 2 }}>↳ {rule.detail}</div>
        )}
      </div>
    </div>
  );
};

// ── main page ─────────────────────────────────────────────────────────────────

const DisciplineDashboard = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await helperService.getDisciplineSummary();
      setSummary(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load discipline summary');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const triggered = summary?.rule_advisories?.filter(r => r.triggered) || [];
  const streakWarn = summary?.streak_active;
  const ddWarn = summary?.drawdown_pct != null && summary.drawdown_pct >= 20;

  return (
    <div style={s.page}>
      {/* ── header ── */}
      <div style={s.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldAlert size={22} color="#a78bfa" />
          <span style={{ fontSize: 20, fontWeight: 800, color: '#f9fafb' }}>Discipline Dashboard</span>
          <span style={s.subtitleChip}>Schwager Ch 16–17</span>
        </div>
        <button onClick={load} disabled={loading} style={s.refreshBtn}>
          <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          Refresh
        </button>
      </div>

      {error && (
        <div style={s.errorBanner}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {summary && (
        <>
          {/* ── stat cards ── */}
          <div style={s.statsGrid}>
            <StatCard
              label="Loss Streak"
              value={summary.recent_losses}
              sub={`Threshold: ${summary.loss_streak_threshold}`}
              warn={streakWarn}
            />
            <StatCard
              label="Streak Active"
              value={summary.streak_active ? 'YES' : 'No'}
              sub={summary.streak_active ? 'Reduce position size' : 'Within tolerance'}
              warn={streakWarn}
            />
            <StatCard
              label="Drawdown"
              value={pct(summary.drawdown_pct)}
              sub={summary.peak_equity ? `Peak: ${summary.peak_equity?.toLocaleString()}` : 'No equity data'}
              warn={ddWarn}
            />
            <StatCard
              label="Rules Triggered"
              value={triggered.length}
              sub={`of ${summary.rule_advisories?.length || 0} monitored rules`}
              warn={triggered.length > 0}
            />
          </div>

          {/* ── recent actions ── */}
          {summary.last_10_actions?.length > 0 && (
            <div style={s.section}>
              <div style={s.sectionTitle}>Last 10 Actions</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {summary.last_10_actions.map((act, i) => {
                  const exitAct = ['SELL', 'COVER', 'REVERSE'].includes(act);
                  const entryAct = ['BUY', 'SELL_SHORT'].includes(act);
                  const color = exitAct ? '#ef4444' : entryAct ? '#10b981' : '#6b7280';
                  return (
                    <span key={i} style={{
                      padding: '3px 10px', borderRadius: 6,
                      background: color + '22', color, fontSize: 11, fontWeight: 700,
                      border: `1px solid ${color}44`,
                    }}>{act}</span>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── triggered violations ── */}
          {triggered.length > 0 && (
            <div style={s.section}>
              <div style={s.sectionTitle}>
                <AlertTriangle size={14} color="#f59e0b" /> Active Rule Violations
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {triggered.map((r, i) => (
                  <ViolationBadge key={i} v={{
                    rule_id: r.rule_id,
                    severity: r.severity,
                    message: r.rule_text + (r.detail ? ` — ${r.detail}` : ''),
                  }} />
                ))}
              </div>
            </div>
          )}

          {/* ── full rules panel ── */}
          <div style={s.section}>
            <div style={s.sectionTitle}>
              <BookOpen size={14} color="#a78bfa" /> Schwager's 10 Key Rules (Ch 17)
            </div>
            {summary.rule_advisories?.map((r, i) => (
              <RuleRow key={i} rule={r} />
            ))}
          </div>
        </>
      )}

      {!summary && !loading && !error && (
        <div style={s.empty}>No discipline data available.</div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

const s = {
  page: { padding: 20, maxWidth: 800, margin: '0 auto', color: '#f9fafb' },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20,
  },
  subtitleChip: {
    background: 'rgba(167,139,250,0.15)', color: '#a78bfa',
    border: '1px solid rgba(167,139,250,0.3)',
    borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 600,
  },
  refreshBtn: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 8,
    padding: '7px 14px', color: '#9ca3af', cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 6, fontSize: 13,
  },
  errorBanner: {
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 8, padding: '10px 14px', color: '#fca5a5',
    display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 14,
  },
  statsGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20,
  },
  statCard: {
    background: '#1f2937', borderRadius: 10, border: '1px solid',
    padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 4,
  },
  section: {
    background: '#1f2937', borderRadius: 10, border: '1px solid #374151',
    padding: 16, marginBottom: 14,
  },
  sectionTitle: {
    fontSize: 13, fontWeight: 700, color: '#d1d5db',
    marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6,
  },
  violationRow: {
    display: 'flex', gap: 10, alignItems: 'flex-start',
    padding: '10px 12px', borderRadius: 8, border: '1px solid',
  },
  empty: { color: '#6b7280', textAlign: 'center', padding: 40 },
};

export default DisciplineDashboard;
