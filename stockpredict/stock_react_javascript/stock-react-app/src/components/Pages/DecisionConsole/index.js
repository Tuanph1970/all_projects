// F-031 / F-102 — DecisionConsole
// Per-symbol: regime ribbon · signal card · action recommendation · stop/target/size · reason chain · pattern overlay
import React, { useState, useCallback } from 'react';
import {
  RefreshCw, ChevronDown, ChevronRight, Shield, Target,
  TrendingUp, TrendingDown, Minus, AlertTriangle, BookOpen,
  Zap, Settings,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import helperService from '../../../services/helperService';
import TradePlanModal from '../../common/TradePlanModal';
import RiskPrefsPanel from './RiskPrefsPanel';
import PatternPanel from './PatternPanel';

// ── helpers ─────────────────────────────────────────────────────────────────

const today = () => new Date().toISOString().split('T')[0];

const REGIME_META = {
  TREND_UP:   { labelKey: 'decision_helper.common.regime_trend_up',   color: '#10b981', icon: TrendingUp },
  TREND_DOWN: { labelKey: 'decision_helper.common.regime_trend_down', color: '#ef4444', icon: TrendingDown },
  RANGE:      { labelKey: 'decision_helper.common.regime_range',      color: '#f59e0b', icon: Minus },
  UNDEFINED:  { labelKey: 'decision_helper.common.regime_undefined',  color: '#6b7280', icon: Minus },
};

const ACTION_META = {
  BUY:        { label: 'BUY',        color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  SELL:       { label: 'SELL',       color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  SELL_SHORT: { label: 'SELL SHORT', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  COVER:      { label: 'COVER',      color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  HOLD:       { label: 'HOLD',       color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)' },
  WAIT:       { label: 'WAIT',       color: '#6b7280', bg: 'rgba(107,114,128,0.15)' },
  REVERSE:    { label: 'REVERSE',    color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)' },
};

const fmt = (v) => v != null ? Number(v).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—';

// ── sub-components ───────────────────────────────────────────────────────────

const RegimePill = ({ regime }) => {
  const { t } = useTranslation();
  const meta = REGIME_META[regime] || REGIME_META.UNDEFINED;
  const Icon = meta.icon;
  return (
    <span style={{ ...styles.pill, background: `${meta.color}22`, color: meta.color, border: `1px solid ${meta.color}44` }}>
      <Icon size={12} />
      {t(meta.labelKey)}
    </span>
  );
};

const ActionCard = ({ rec, onPlan }) => {
  const { t } = useTranslation();
  const meta = ACTION_META[rec.action] || ACTION_META.WAIT;
  const isEntry = ['BUY', 'SELL_SHORT'].includes(rec.action);
  return (
    <div style={{ ...styles.card, borderColor: meta.color + '55' }}>
      <div style={styles.actionRow}>
        <span style={{ ...styles.actionBadge, background: meta.bg, color: meta.color }}>
          {meta.label}
        </span>
        <span style={styles.confidence}>
          {t('decision_helper.decision_console.confidence_label', { pct: (rec.confidence * 100).toFixed(0) })}
        </span>
        {isEntry && (
          <button onClick={onPlan} style={styles.planBtn}>
            <BookOpen size={14} />
            {t('decision_helper.decision_console.save_plan')}
          </button>
        )}
      </div>

      <div style={styles.priceGrid}>
        <PriceBox label={t('decision_helper.decision_console.entry')} value={fmt(rec.entry_price)} color="#f9fafb" />
        <PriceBox label={t('decision_helper.decision_console.stop')} value={fmt(rec.stop_price)} color="#ef4444" icon={Shield} />
        <PriceBox label={t('decision_helper.decision_console.target')} value={fmt(rec.target_price)} color="#10b981" icon={Target} />
        <PriceBox label={t('decision_helper.decision_console.shares')} value={rec.position_size ?? '—'} color="#f9fafb" />
      </div>

      {rec.stop_price && rec.entry_price && rec.target_price && (
        <RRBar entry={rec.entry_price} stop={rec.stop_price} target={rec.target_price} />
      )}

      <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>
        {t('decision_helper.decision_console.signal_label')}: <span style={{ color: '#374151' }}>{rec.signal_kind || '—'}</span>
        {rec.signal_confirmed && <span style={styles.confirmedTag}>{t('decision_helper.decision_console.confirmed')}</span>}
        &nbsp;· {t('decision_helper.decision_console.state_label')}: {rec.state_before} → {rec.state_after}
      </div>
    </div>
  );
};

const PriceBox = ({ label, value, color, icon: Icon }) => (
  <div style={styles.priceBox}>
    <div style={{ fontSize: 10, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.5, display: 'flex', alignItems: 'center', gap: 3 }}>
      {Icon && <Icon size={10} />} {label}
    </div>
    <div style={{ fontSize: 16, fontWeight: 700, color: color === '#f9fafb' ? '#111827' : color }}>{value}</div>
  </div>
);

const RRBar = ({ entry, stop, target }) => {
  const rr = Math.abs(target - entry) / Math.abs(entry - stop);
  const good = rr >= 1.5;
  return (
    <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
      <span style={{ color: '#9ca3af' }}>R:R</span>
      <div style={{ flex: 1, height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${Math.min(rr / 3 * 100, 100)}%`, background: good ? '#10b981' : '#f59e0b', borderRadius: 3 }} />
      </div>
      <span style={{ color: good ? '#10b981' : '#f59e0b', fontWeight: 600 }}>
        {rr.toFixed(2)}:1
      </span>
    </div>
  );
};

const DisciplinePanel = ({ violations }) => {
  if (!violations || violations.length === 0) return null;
  const blocks = violations.filter(v => v.severity === 'BLOCK');
  const warnings = violations.filter(v => v.severity === 'WARNING');
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {blocks.map((v, i) => (
        <div key={i} style={{
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.35)',
          borderRadius: 8, padding: '9px 13px', display: 'flex', gap: 8, alignItems: 'flex-start',
        }}>
          <AlertTriangle size={14} style={{ color: '#ef4444', marginTop: 1, flexShrink: 0 }} />
          <div>
            <span style={{ color: '#ef4444', fontWeight: 700, fontSize: 12, marginRight: 6 }}>
              BLOCK [{v.rule_id}]
            </span>
            <span style={{ color: '#dc2626', fontSize: 12 }}>{v.message}</span>
          </div>
        </div>
      ))}
      {warnings.map((v, i) => (
        <div key={i} style={{
          background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)',
          borderRadius: 8, padding: '9px 13px', display: 'flex', gap: 8, alignItems: 'flex-start',
        }}>
          <AlertTriangle size={14} style={{ color: '#f59e0b', marginTop: 1, flexShrink: 0 }} />
          <div>
            <span style={{ color: '#f59e0b', fontWeight: 700, fontSize: 12, marginRight: 6 }}>
              WARN [{v.rule_id}]
            </span>
            <span style={{ color: '#b45309', fontSize: 12 }}>{v.message}</span>
          </div>
        </div>
      ))}
    </div>
  );
};

const ReasonChain = ({ steps }) => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  if (!steps || steps.length === 0) return null;
  return (
    <div style={styles.card}>
      <button onClick={() => setOpen(o => !o)} style={styles.reasonToggle}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {t('decision_helper.decision_console.reason_chain', { count: steps.length })}
      </button>
      {open && (
        <div style={{ marginTop: 10 }}>
          {steps.map((s, i) => (
            <div key={i} style={styles.reasonStep}>
              <span style={styles.stageTag}>{s.stage}</span>
              <span style={{ color: '#374151', fontSize: 12 }}>{s.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ── main page ────────────────────────────────────────────────────────────────

const DecisionConsole = () => {
  const { t } = useTranslation();
  const [tickerInput, setTickerInput] = useState('');
  const [barDate, setBarDate] = useState(today());
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [planOpen, setPlanOpen] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);
  const [patterns, setPatterns] = useState(null);
  const [patternsLoading, setPatternsLoading] = useState(false);
  const [patternsError, setPatternsError] = useState(null);

  const run = useCallback(async () => {
    const ticker = tickerInput.trim().toUpperCase();
    if (!ticker) return;
    setLoading(true);
    setError(null);
    setPatterns(null);
    setPatternsError(null);
    setPatternsLoading(true);
    try {
      // F-102: fetch recommendation + patterns in parallel (best-effort)
      const [recResult, patternResult] = await Promise.allSettled([
        helperService.recommend({ ticker, barDate }),
        helperService.getPatterns(ticker),
      ]);
      if (recResult.status === 'fulfilled') {
        setRec(recResult.value);
      } else {
        setError(recResult.reason?.response?.data?.detail || recResult.reason?.message || 'Request failed');
      }
      if (patternResult.status === 'fulfilled') {
        setPatterns(patternResult.value?.patterns ?? []);
      } else {
        setPatternsError(true);
      }
    } finally {
      setLoading(false);
      setPatternsLoading(false);
    }
  }, [tickerInput, barDate]);

  const handleKey = (e) => { if (e.key === 'Enter') run(); };

  return (
    <div style={styles.page}>
      {/* ── toolbar ── */}
      <div style={styles.toolbar}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flex: 1 }}>
          <input
            value={tickerInput}
            onChange={e => setTickerInput(e.target.value.toUpperCase())}
            onKeyDown={handleKey}
            placeholder={t('decision_helper.decision_console.ticker_placeholder')}
            style={styles.tickerInput}
          />
          <input
            type="date"
            value={barDate}
            onChange={e => setBarDate(e.target.value)}
            style={styles.dateInput}
          />
          <button onClick={run} disabled={loading || !tickerInput.trim()} style={styles.runBtn}>
            {loading
              ? <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} />
              : <Zap size={15} />}
            {loading ? t('decision_helper.common.analyzing') : t('decision_helper.decision_console.analyze')}
          </button>
        </div>
        <button onClick={() => setShowPrefs(p => !p)} style={styles.iconBtn} title={t('decision_helper.decision_console.risk_prefs_title')}>
          <Settings size={16} />
        </button>
      </div>

      {showPrefs && <RiskPrefsPanel onClose={() => setShowPrefs(false)} />}

      {error && (
        <div style={styles.errorBanner}>
          <AlertTriangle size={14} />
          {error}
        </div>
      )}

      {rec && (
        <div style={styles.content}>
          {/* ── header row ── */}
          <div style={styles.headerRow}>
            <span style={styles.tickerLabel}>{rec.ticker}</span>
            <RegimePill regime={rec.regime} />
            <span style={{ color: '#9ca3af', fontSize: 12 }}>
              {rec.bar_date} · {rec.latency_ms}ms
            </span>
          </div>

          {/* ── action card ── */}
          <ActionCard rec={rec} onPlan={() => setPlanOpen(true)} />

          {/* ── pattern overlay (F-102) ── */}
          <PatternPanel
            patterns={patterns}
            loading={patternsLoading}
            error={patternsError}
          />

          {/* ── discipline violations ── */}
          <DisciplinePanel violations={rec.discipline_violations} />

          {/* ── reason chain ── */}
          <ReasonChain steps={rec.reason_chain} />
        </div>
      )}

      {!rec && !loading && !error && (
        <div style={styles.empty}>
          {t('decision_helper.decision_console.empty_hint')}
        </div>
      )}

      <TradePlanModal
        isOpen={planOpen}
        onClose={() => setPlanOpen(false)}
        recommendation={rec}
        onSaved={() => {}}
      />

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

const styles = {
  page: { padding: 20, maxWidth: 720, margin: '0 auto', color: '#111827' },
  toolbar: { display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16 },
  tickerInput: {
    background: '#ffffff', border: '1px solid #d1d5db', borderRadius: 8,
    padding: '9px 14px', color: '#111827', fontSize: 15, fontWeight: 700,
    width: 130, outline: 'none', textTransform: 'uppercase',
  },
  dateInput: {
    background: '#ffffff', border: '1px solid #d1d5db', borderRadius: 8,
    padding: '9px 12px', color: '#111827', fontSize: 13, outline: 'none',
  },
  runBtn: {
    background: '#3b82f6', border: 'none', borderRadius: 8,
    padding: '9px 18px', color: '#fff', fontWeight: 600, fontSize: 14,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
  },
  iconBtn: {
    background: '#ffffff', border: '1px solid #d1d5db', borderRadius: 8,
    padding: '8px 10px', color: '#6b7280', cursor: 'pointer',
    display: 'flex', alignItems: 'center',
  },
  errorBanner: {
    background: '#fee2e2', border: '1px solid #fca5a5',
    borderRadius: 8, padding: '10px 14px', color: '#dc2626',
    display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 12,
  },
  content: { display: 'flex', flexDirection: 'column', gap: 12 },
  headerRow: { display: 'flex', alignItems: 'center', gap: 10 },
  tickerLabel: { fontSize: 22, fontWeight: 800, color: '#111827' },
  pill: {
    display: 'inline-flex', alignItems: 'center', gap: 5,
    padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
  },
  card: {
    background: '#ffffff', borderRadius: 10,
    border: '1px solid #e5e7eb', padding: 16,
  },
  actionRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 },
  actionBadge: {
    padding: '5px 14px', borderRadius: 8, fontWeight: 700,
    fontSize: 14, letterSpacing: 1,
  },
  confidence: { fontSize: 12, color: '#6b7280', flex: 1 },
  planBtn: {
    background: '#3b82f6', border: 'none', borderRadius: 7,
    padding: '6px 14px', color: '#fff', fontWeight: 600, fontSize: 13,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
  },
  priceGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12,
  },
  priceBox: {
    background: '#f9fafb', borderRadius: 8, padding: '10px 12px',
  },
  confirmedTag: {
    background: 'rgba(16,185,129,0.15)', color: '#059669',
    borderRadius: 4, padding: '1px 6px', fontSize: 10, fontWeight: 600,
    marginLeft: 4,
  },
  reasonToggle: {
    background: 'none', border: 'none', color: '#6b7280',
    cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 5,
    padding: 0,
  },
  reasonStep: {
    display: 'flex', gap: 8, alignItems: 'flex-start',
    padding: '6px 0', borderBottom: '1px solid #f3f4f6',
  },
  stageTag: {
    background: '#f3f4f6', color: '#6b7280', borderRadius: 4,
    padding: '1px 6px', fontSize: 10, fontWeight: 600,
    whiteSpace: 'nowrap', flexShrink: 0,
  },
  empty: { color: '#6b7280', textAlign: 'center', marginTop: 60, fontSize: 14 },
};

export default DecisionConsole;
