// F-064 — DisciplineDashboard (Phase G)
// Schwager Ch 16-17: streak tracker, drawdown alert, rule-advisory panel
import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert, TrendingDown, CheckCircle, XCircle,
  AlertTriangle, Info, RefreshCw, BookOpen,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import helperService from '../../../services/helperService';

// ── helpers ──────────────────────────────────────────────────────────────────

const SEVERITY_META = {
  BLOCK:   { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', Icon: XCircle },
  WARNING: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', Icon: AlertTriangle },
  INFO:    { color: '#6b7280', bg: 'rgba(107,114,128,0.10)', Icon: Info },
};

const pct = (v) => v != null ? `${Number(v).toFixed(1)}%` : '—';

// ── sub-components ────────────────────────────────────────────────────────────

const StatCard = ({ label, value, sub, color = '#111827', warn = false }) => (
  <div style={{ ...s.statCard, borderColor: warn ? '#f59e0b44' : '#e5e7eb' }}>
    <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 800, color: warn ? '#f59e0b' : color, lineHeight: 1.2 }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sub}</div>}
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
        <span style={{ color: '#374151', fontSize: 12 }}>{v.message}</span>
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
      padding: '8px 0', borderBottom: '1px solid #f3f4f6',
    }}>
      <Icon size={14} style={{ color: rule.triggered ? meta.color : '#6b7280', marginTop: 2, flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 700, fontSize: 12, color: rule.triggered ? meta.color : '#374151' }}>
            {rule.rule_id}
          </span>
          <span style={{ fontSize: 11, color: '#6b7280' }}>{rule.chapter}</span>
        </div>
        <div style={{ fontSize: 12, color: rule.triggered ? '#111827' : '#374151', marginTop: 2 }}>
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
  const { t } = useTranslation();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await helperService.getDisciplineSummary();
    if (res?.success) {
      setSummary(res.data);
    } else {
      setError(res?.error?.message || 'Failed to load discipline summary');
    }
    setLoading(false);
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
          <span style={{ fontSize: 20, fontWeight: 800, color: '#111827' }}>{t('decision_helper.discipline.title')}</span>
          <span style={s.subtitleChip}>{t('decision_helper.discipline.subtitle')}</span>
        </div>
        <button onClick={load} disabled={loading} style={s.refreshBtn}>
          <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          {t('decision_helper.common.refresh')}
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
          <div className="responsive-stack responsive-stack-2up" style={s.statsGrid}>
            <StatCard
              label={t('decision_helper.discipline.loss_streak')}
              value={summary.recent_losses}
              sub={t('decision_helper.discipline.threshold', { n: summary.loss_streak_threshold })}
              warn={streakWarn}
            />
            <StatCard
              label={t('decision_helper.discipline.streak_active')}
              value={summary.streak_active ? 'YES' : 'No'}
              sub={summary.streak_active ? t('decision_helper.discipline.reduce_size') : t('decision_helper.discipline.within_tolerance')}
              warn={streakWarn}
            />
            <StatCard
              label={t('decision_helper.discipline.drawdown')}
              value={pct(summary.drawdown_pct)}
              sub={summary.peak_equity ? t('decision_helper.discipline.peak', { n: summary.peak_equity?.toLocaleString() }) : t('decision_helper.discipline.no_equity')}
              warn={ddWarn}
            />
            <StatCard
              label={t('decision_helper.discipline.rules_triggered')}
              value={triggered.length}
              sub={t('decision_helper.discipline.of_rules', { total: summary.rule_advisories?.length || 0 })}
              warn={triggered.length > 0}
            />
          </div>

          {/* ── recent actions ── */}
          {summary.last_10_actions?.length > 0 && (
            <div style={s.section}>
              <div style={s.sectionTitle}>{t('decision_helper.discipline.last_10_actions')}</div>
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
                <AlertTriangle size={14} color="#f59e0b" /> {t('decision_helper.discipline.active_violations')}
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
              <BookOpen size={14} color="#a78bfa" /> {t('decision_helper.discipline.schwager_rules')}
            </div>
            {summary.rule_advisories?.map((r, i) => (
              <RuleRow key={i} rule={r} />
            ))}
          </div>
        </>
      )}

      {!summary && !loading && !error && (
        <div style={s.empty}>{t('decision_helper.discipline.no_data')}</div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

const s = {
  page: { padding: 20, maxWidth: 800, margin: '0 auto', color: '#111827' },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20,
  },
  subtitleChip: {
    background: 'rgba(167,139,250,0.15)', color: '#7c3aed',
    border: '1px solid rgba(167,139,250,0.3)',
    borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 600,
  },
  refreshBtn: {
    background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 8,
    padding: '7px 14px', color: '#6b7280', cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 6, fontSize: 13,
  },
  errorBanner: {
    background: '#fee2e2', border: '1px solid #fca5a5',
    borderRadius: 8, padding: '10px 14px', color: '#dc2626',
    display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 14,
  },
  statsGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20,
  },
  statCard: {
    background: '#ffffff', borderRadius: 10, border: '1px solid',
    padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 4,
  },
  section: {
    background: '#ffffff', borderRadius: 10, border: '1px solid #e5e7eb',
    padding: 16, marginBottom: 14,
  },
  sectionTitle: {
    fontSize: 13, fontWeight: 700, color: '#374151',
    marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6,
  },
  violationRow: {
    display: 'flex', gap: 10, alignItems: 'flex-start',
    padding: '10px 12px', borderRadius: 8, border: '1px solid',
  },
  empty: { color: '#9ca3af', textAlign: 'center', padding: 40 },
};

export default DisciplineDashboard;
