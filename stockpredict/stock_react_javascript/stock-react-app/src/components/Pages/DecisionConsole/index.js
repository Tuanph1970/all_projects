// F-031 — DecisionConsole
// Per-symbol: regime ribbon · signal card · action recommendation · stop/target/size · reason chain
import React, { useState, useCallback } from 'react';
import {
  RefreshCw, ChevronDown, ChevronRight, Shield, Target,
  TrendingUp, TrendingDown, Minus, AlertTriangle, BookOpen,
  Zap, Settings,
} from 'lucide-react';
import helperService from '../../../services/helperService';
import TradePlanModal from '../../common/TradePlanModal';
import RiskPrefsPanel from './RiskPrefsPanel';

// ── helpers ─────────────────────────────────────────────────────────────────

const today = () => new Date().toISOString().split('T')[0];

const REGIME_META = {
  TREND_UP:   { label: 'Trend ↑',   color: '#10b981', icon: TrendingUp },
  TREND_DOWN: { label: 'Trend ↓',   color: '#ef4444', icon: TrendingDown },
  RANGE:      { label: 'Range',     color: '#f59e0b', icon: Minus },
  UNDEFINED:  { label: 'Undefined', color: '#6b7280', icon: Minus },
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
  const meta = REGIME_META[regime] || REGIME_META.UNDEFINED;
  const Icon = meta.icon;
  return (
    <span style={{ ...styles.pill, background: `${meta.color}22`, color: meta.color, border: `1px solid ${meta.color}44` }}>
      <Icon size={12} />
      {meta.label}
    </span>
  );
};

const ActionCard = ({ rec, onPlan }) => {
  const meta = ACTION_META[rec.action] || ACTION_META.WAIT;
  const isEntry = ['BUY', 'SELL_SHORT'].includes(rec.action);
  return (
    <div style={{ ...styles.card, borderColor: meta.color + '55' }}>
      <div style={styles.actionRow}>
        <span style={{ ...styles.actionBadge, background: meta.bg, color: meta.color }}>
          {meta.label}
        </span>
        <span style={styles.confidence}>
          Confidence {(rec.confidence * 100).toFixed(0)}%
        </span>
        {isEntry && (
          <button onClick={onPlan} style={styles.planBtn}>
            <BookOpen size={14} />
            Save Plan
          </button>
        )}
      </div>

      <div style={styles.priceGrid}>
        <PriceBox label="Entry" value={fmt(rec.entry_price)} color="#f9fafb" />
        <PriceBox label="Stop" value={fmt(rec.stop_price)} color="#ef4444" icon={Shield} />
        <PriceBox label="Target" value={fmt(rec.target_price)} color="#10b981" icon={Target} />
        <PriceBox label="Shares" value={rec.position_size ?? '—'} color="#f9fafb" />
      </div>

      {rec.stop_price && rec.entry_price && rec.target_price && (
        <RRBar entry={rec.entry_price} stop={rec.stop_price} target={rec.target_price} />
      )}

      <div style={{ marginTop: 8, fontSize: 12, color: '#9ca3af' }}>
        Signal: <span style={{ color: '#d1d5db' }}>{rec.signal_kind || '—'}</span>
        {rec.signal_confirmed && <span style={styles.confirmedTag}>confirmed</span>}
        &nbsp;· State: {rec.state_before} → {rec.state_after}
      </div>
    </div>
  );
};

const PriceBox = ({ label, value, color, icon: Icon }) => (
  <div style={styles.priceBox}>
    <div style={{ fontSize: 10, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.5, display: 'flex', alignItems: 'center', gap: 3 }}>
      {Icon && <Icon size={10} />} {label}
    </div>
    <div style={{ fontSize: 16, fontWeight: 700, color }}>{value}</div>
  </div>
);

const RRBar = ({ entry, stop, target }) => {
  const rr = Math.abs(target - entry) / Math.abs(entry - stop);
  const good = rr >= 1.5;
  return (
    <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
      <span style={{ color: '#6b7280' }}>R:R</span>
      <div style={{ flex: 1, height: 6, background: '#374151', borderRadius: 3, overflow: 'hidden' }}>
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
            <span style={{ color: '#fca5a5', fontSize: 12 }}>{v.message}</span>
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
            <span style={{ color: '#fcd34d', fontSize: 12 }}>{v.message}</span>
          </div>
        </div>
      ))}
    </div>
  );
};

const ReasonChain = ({ steps }) => {
  const [open, setOpen] = useState(false);
  if (!steps || steps.length === 0) return null;
  return (
    <div style={styles.card}>
      <button onClick={() => setOpen(o => !o)} style={styles.reasonToggle}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Reason chain ({steps.length} steps)
      </button>
      {open && (
        <div style={{ marginTop: 10 }}>
          {steps.map((s, i) => (
            <div key={i} style={styles.reasonStep}>
              <span style={styles.stageTag}>{s.stage}</span>
              <span style={{ color: '#d1d5db', fontSize: 12 }}>{s.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ── main page ────────────────────────────────────────────────────────────────

const DecisionConsole = () => {
  const [tickerInput, setTickerInput] = useState('');
  const [barDate, setBarDate] = useState(today());
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [planOpen, setPlanOpen] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);

  const run = useCallback(async () => {
    const ticker = tickerInput.trim().toUpperCase();
    if (!ticker) return;
    setLoading(true);
    setError(null);
    try {
      const data = await helperService.recommend({ ticker, barDate });
      setRec(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Request failed');
    } finally {
      setLoading(false);
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
            placeholder="Ticker (e.g. VIC)"
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
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
        </div>
        <button onClick={() => setShowPrefs(p => !p)} style={styles.iconBtn} title="Risk preferences">
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
            <span style={{ color: '#6b7280', fontSize: 12 }}>
              {rec.bar_date} · {rec.latency_ms}ms
            </span>
          </div>

          {/* ── action card ── */}
          <ActionCard rec={rec} onPlan={() => setPlanOpen(true)} />

          {/* ── discipline violations ── */}
          <DisciplinePanel violations={rec.discipline_violations} />

          {/* ── reason chain ── */}
          <ReasonChain steps={rec.reason_chain} />
        </div>
      )}

      {!rec && !loading && !error && (
        <div style={styles.empty}>
          Enter a ticker symbol and press Analyze to get a recommendation.
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
  page: { padding: 20, maxWidth: 720, margin: '0 auto', color: '#f9fafb' },
  toolbar: { display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16 },
  tickerInput: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 8,
    padding: '9px 14px', color: '#f9fafb', fontSize: 15, fontWeight: 700,
    width: 130, outline: 'none', textTransform: 'uppercase',
  },
  dateInput: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 8,
    padding: '9px 12px', color: '#f9fafb', fontSize: 13, outline: 'none',
  },
  runBtn: {
    background: '#3b82f6', border: 'none', borderRadius: 8,
    padding: '9px 18px', color: '#fff', fontWeight: 600, fontSize: 14,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
  },
  iconBtn: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 8,
    padding: '8px 10px', color: '#9ca3af', cursor: 'pointer',
    display: 'flex', alignItems: 'center',
  },
  errorBanner: {
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 8, padding: '10px 14px', color: '#fca5a5',
    display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 12,
  },
  content: { display: 'flex', flexDirection: 'column', gap: 12 },
  headerRow: { display: 'flex', alignItems: 'center', gap: 10 },
  tickerLabel: { fontSize: 22, fontWeight: 800, color: '#f9fafb' },
  pill: {
    display: 'inline-flex', alignItems: 'center', gap: 5,
    padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
  },
  card: {
    background: '#1f2937', borderRadius: 10,
    border: '1px solid #374151', padding: 16,
  },
  actionRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 },
  actionBadge: {
    padding: '5px 14px', borderRadius: 8, fontWeight: 700,
    fontSize: 14, letterSpacing: 1,
  },
  confidence: { fontSize: 12, color: '#9ca3af', flex: 1 },
  planBtn: {
    background: '#3b82f6', border: 'none', borderRadius: 7,
    padding: '6px 14px', color: '#fff', fontWeight: 600, fontSize: 13,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
  },
  priceGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12,
  },
  priceBox: {
    background: '#111827', borderRadius: 8, padding: '10px 12px',
  },
  confirmedTag: {
    background: 'rgba(16,185,129,0.15)', color: '#10b981',
    borderRadius: 4, padding: '1px 6px', fontSize: 10, fontWeight: 600,
    marginLeft: 4,
  },
  reasonToggle: {
    background: 'none', border: 'none', color: '#9ca3af',
    cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 5,
    padding: 0,
  },
  reasonStep: {
    display: 'flex', gap: 8, alignItems: 'flex-start',
    padding: '6px 0', borderBottom: '1px solid #1f2937',
  },
  stageTag: {
    background: '#374151', color: '#9ca3af', borderRadius: 4,
    padding: '1px 6px', fontSize: 10, fontWeight: 600,
    whiteSpace: 'nowrap', flexShrink: 0,
  },
  empty: { color: '#6b7280', textAlign: 'center', marginTop: 60, fontSize: 14 },
};

export default DecisionConsole;
