// F-122..F-123 — ScannerPage: multi-ticker decision scanner
import React, { useState } from 'react';
import {
  Scan, RefreshCw, TrendingUp, TrendingDown, Minus,
  AlertTriangle, BookOpen, Shield, Target, CheckCircle,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import helperService from '../../../services/helperService';
import TradePlanModal from '../../common/TradePlanModal';

const today = () => new Date().toISOString().split('T')[0];

const fmt = (v) => v != null
  ? Number(v).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  : '—';

const ACTION_META = {
  BUY:        { label: 'BUY',        color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  SELL_SHORT: { label: 'SELL SHORT', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  SELL:       { label: 'SELL',       color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  COVER:      { label: 'COVER',      color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  REVERSE:    { label: 'REVERSE',    color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)' },
  HOLD:       { label: 'HOLD',       color: '#6b7280', bg: 'rgba(107,114,128,0.12)' },
  WAIT:       { label: 'WAIT',       color: '#4b5563', bg: 'rgba(75,85,99,0.12)' },
};

const REGIME_META = {
  TREND_UP:   { labelKey: 'decision_helper.common.regime_trend_up',   color: '#10b981', Icon: TrendingUp },
  TREND_DOWN: { labelKey: 'decision_helper.common.regime_trend_down', color: '#ef4444', Icon: TrendingDown },
  RANGE:      { labelKey: 'decision_helper.common.regime_range',      color: '#f59e0b', Icon: Minus },
  UNDEFINED:  { labelKey: null,                                        color: '#6b7280', Icon: Minus },
};

const FILTERS = ['All', 'Actionable', 'BUY', 'SELL_SHORT', 'HOLD', 'WAIT'];

// ── Sub-components ────────────────────────────────────────────────────────────

const ActionBadge = ({ action }) => {
  const m = ACTION_META[action] || ACTION_META.WAIT;
  return (
    <span style={{
      background: m.bg, color: m.color, fontWeight: 700, fontSize: 11,
      padding: '3px 9px', borderRadius: 5, letterSpacing: 0.5, whiteSpace: 'nowrap',
    }}>
      {m.label}
    </span>
  );
};

const RegimePill = ({ regime }) => {
  const { t } = useTranslation();
  const m = REGIME_META[regime] || REGIME_META.UNDEFINED;
  const { Icon } = m;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      color: m.color, fontSize: 11, fontWeight: 600,
      background: `${m.color}18`, padding: '2px 7px', borderRadius: 10,
      border: `1px solid ${m.color}33`,
    }}>
      <Icon size={10} />
      {m.labelKey ? t(m.labelKey) : '—'}
    </span>
  );
};

const ConfBar = ({ value }) => {
  const pct = Math.round((value ?? 0) * 100);
  const color = pct >= 70 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#6b7280';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 80 }}>
      <div style={{ flex: 1, height: 5, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 11, color, fontWeight: 600, width: 28, textAlign: 'right' }}>{pct}%</span>
    </div>
  );
};

// ── SummaryBar ────────────────────────────────────────────────────────────────

const SummaryBar = ({ result }) => {
  const { t } = useTranslation();
  const buys = result.results.filter(r => r.action === 'BUY').length;
  const shorts = result.results.filter(r => r.action === 'SELL_SHORT').length;
  return (
    <div style={styles.summaryBar}>
      <span style={styles.summaryItem}>
        {t('decision_helper.scanner.scanned', { count: result.ticker_count })}
      </span>
      <span style={{ color: '#6b7280' }}>·</span>
      <span style={styles.summaryItem}>
        <span style={{ color: '#10b981', fontWeight: 700 }}>{buys} BUY</span>
      </span>
      <span style={{ color: '#6b7280' }}>·</span>
      <span style={styles.summaryItem}>
        <span style={{ color: '#f59e0b', fontWeight: 700 }}>{shorts} SELL SHORT</span>
      </span>
      <span style={{ color: '#6b7280' }}>·</span>
      <span style={{ fontSize: 12, color: '#6b7280' }}>{result.latency_ms}ms</span>
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

const ScannerPage = () => {
  const { t } = useTranslation();
  const [barDate, setBarDate] = useState(today());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [filter, setFilter] = useState('All');
  const [planRec, setPlanRec] = useState(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    const res = await helperService.scan(barDate);
    if (res?.success) {
      setResult(res.data);
      setFilter(res.data?.actionable_count === 0 ? 'All' : 'Actionable');
    } else {
      setError(res?.error?.message || 'Scan failed');
    }
    setLoading(false);
  };

  const filtered = result?.results?.filter(r => {
    if (filter === 'All') return true;
    if (filter === 'Actionable') return r.is_actionable;
    return r.action === filter;
  }) ?? [];

  // Build a fake recommendation object TradePlanModal expects
  const buildRec = (item) => ({
    ticker: item.ticker,
    action: item.action,
    bar_date: result.bar_date,
    entry_price: item.entry_price,
    stop_price: item.stop_price,
    target_price: item.target_price,
    position_size: item.position_size,
    signal_kind: item.signal_kind,
    signal_confirmed: item.signal_confirmed,
    regime: item.regime,
    confidence: item.confidence,
    reason_chain: [],
    discipline_violations: [],
  });

  return (
    <div style={styles.page}>
      {/* ── Toolbar ── */}
      <div style={styles.toolbar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Scan size={18} color="#a78bfa" />
          <span style={{ fontWeight: 700, fontSize: 16, color: '#111827' }}>{t('decision_helper.scanner.title')}</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginLeft: 'auto' }}>
          <input
            type="date"
            value={barDate}
            onChange={e => setBarDate(e.target.value)}
            style={styles.dateInput}
          />
          <button onClick={run} disabled={loading} style={styles.runBtn}>
            {loading
              ? <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />
              : <Scan size={14} />}
            {loading ? t('decision_helper.common.scanning') : t('decision_helper.scanner.scan_all')}
          </button>
        </div>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          <AlertTriangle size={14} />
          {error}
        </div>
      )}

      {!result && !loading && !error && (
        <div style={styles.empty}>
          <Scan size={40} color="#374151" style={{ marginBottom: 12 }} />
          <div style={{ fontWeight: 600, color: '#6b7280', marginBottom: 4 }}>{t('decision_helper.scanner.no_scan_title')}</div>
          <div style={{ fontSize: 13, color: '#4b5563' }}>{t('decision_helper.scanner.no_scan_hint')}</div>
        </div>
      )}

      {result && (
        <>
          <SummaryBar result={result} />

          {/* ── Filter bar ── */}
          <div style={styles.filterBar}>
            {FILTERS.map(f => {
              const count = f === 'All' ? result.results.length
                : f === 'Actionable' ? result.actionable_count
                : result.results.filter(r => r.action === f).length;
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  style={{
                    ...styles.filterBtn,
                    background: filter === f ? '#e5e7eb' : 'transparent',
                    color: filter === f ? '#111827' : '#6b7280',
                    borderColor: filter === f ? '#d1d5db' : 'transparent',
                  }}
                >
                  {f === 'All' ? t('decision_helper.scanner.filter_all') : f === 'Actionable' ? t('decision_helper.scanner.filter_actionable') : f} {count > 0 && <span style={styles.filterCount}>{count}</span>}
                </button>
              );
            })}
          </div>

          {/* ── Results table ── */}
          {filtered.length === 0 ? (
            <div style={{ ...styles.empty, marginTop: 24 }}>
              <div style={{ color: '#6b7280', fontSize: 13 }}>{t('decision_helper.scanner.no_results')}</div>
            </div>
          ) : (
            <div style={styles.tableWrap}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    {[t('decision_helper.scanner.col_action'), t('decision_helper.scanner.col_ticker'), t('decision_helper.scanner.col_regime'), t('decision_helper.scanner.col_confidence'), t('decision_helper.scanner.col_entry'), t('decision_helper.scanner.col_stop'), t('decision_helper.scanner.col_target'), t('decision_helper.scanner.col_signal'), ''].map(h => (
                      <th key={h} style={styles.th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((item, i) => (
                    <tr key={item.ticker} style={{ ...styles.tr, background: i % 2 === 0 ? '#f9fafb' : '#ffffff' }}>
                      <td style={styles.td}><ActionBadge action={item.action} /></td>
                      <td style={{ ...styles.td, fontWeight: 700, color: '#111827', fontSize: 14 }}>
                        {item.ticker}
                        {item.error && (
                          <span title={item.error} style={{ marginLeft: 6 }}>
                            <AlertTriangle size={12} color="#ef4444" />
                          </span>
                        )}
                      </td>
                      <td style={styles.td}><RegimePill regime={item.regime} /></td>
                      <td style={styles.td}><ConfBar value={item.confidence} /></td>
                      <td style={styles.td}>{fmt(item.entry_price)}</td>
                      <td style={{ ...styles.td, color: '#ef4444' }}>
                        {item.stop_price ? (
                          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Shield size={11} /> {fmt(item.stop_price)}
                          </span>
                        ) : '—'}
                      </td>
                      <td style={{ ...styles.td, color: '#10b981' }}>
                        {item.target_price ? (
                          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Target size={11} /> {fmt(item.target_price)}
                          </span>
                        ) : '—'}
                      </td>
                      <td style={styles.td}>
                        {item.signal_kind ? (
                          <span style={{ fontSize: 11, color: '#9ca3af' }}>
                            {item.signal_kind}
                            {item.signal_confirmed && (
                              <CheckCircle size={11} color="#10b981" style={{ marginLeft: 4, verticalAlign: 'middle' }} />
                            )}
                          </span>
                        ) : '—'}
                      </td>
                      <td style={styles.td}>
                        {item.is_actionable && (
                          <button
                            onClick={() => setPlanRec(buildRec(item))}
                            style={styles.planBtn}
                          >
                            <BookOpen size={12} /> {t('decision_helper.scanner.plan')}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <TradePlanModal
        isOpen={planRec !== null}
        onClose={() => setPlanRec(null)}
        recommendation={planRec}
        onSaved={() => setPlanRec(null)}
      />

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

const styles = {
  page: { padding: 20, maxWidth: 1100, margin: '0 auto', color: '#111827' },
  toolbar: { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 },
  dateInput: {
    background: '#ffffff', border: '1px solid #d1d5db', borderRadius: 8,
    padding: '8px 12px', color: '#111827', fontSize: 13, outline: 'none',
  },
  runBtn: {
    background: '#7c3aed', border: 'none', borderRadius: 8,
    padding: '9px 18px', color: '#fff', fontWeight: 700, fontSize: 14,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
  },
  errorBanner: {
    background: '#fee2e2', border: '1px solid #fca5a5',
    borderRadius: 8, padding: '10px 14px', color: '#dc2626',
    display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 12,
  },
  empty: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', minHeight: 200, textAlign: 'center',
  },
  summaryBar: {
    display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
    background: '#f9fafb', borderRadius: 8, padding: '10px 16px',
    marginBottom: 12, fontSize: 13, color: '#374151',
  },
  summaryItem: { display: 'flex', alignItems: 'center', gap: 4 },
  filterBar: { display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 12 },
  filterBtn: {
    border: '1px solid transparent', borderRadius: 6,
    padding: '5px 12px', fontSize: 12, fontWeight: 600, cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 5, transition: 'all 0.15s',
  },
  filterCount: {
    background: '#e5e7eb', color: '#6b7280', fontSize: 10,
    padding: '1px 5px', borderRadius: 8, fontWeight: 700,
  },
  tableWrap: { overflowX: 'auto', borderRadius: 10, border: '1px solid #e5e7eb' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: {
    background: '#f9fafb', padding: '10px 12px', textAlign: 'left',
    color: '#6b7280', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5,
    borderBottom: '1px solid #e5e7eb', whiteSpace: 'nowrap',
  },
  tr: { borderBottom: '1px solid #f3f4f6' },
  td: { padding: '10px 12px', verticalAlign: 'middle' },
  planBtn: {
    background: '#3b82f6', border: 'none', borderRadius: 5,
    padding: '5px 10px', color: '#fff', fontWeight: 600, fontSize: 11,
    cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4,
  },
};

export default ScannerPage;
