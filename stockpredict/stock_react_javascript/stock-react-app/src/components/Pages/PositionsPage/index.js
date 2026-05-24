// F-152..F-153 — PositionsPage: open positions dashboard
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, RefreshCw, AlertTriangle,
  Edit2, Check, X, Zap, Shield,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import helperService from '../../../services/helperService';

const fmt = (v) => v != null
  ? Number(v).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  : '—';

const daysSince = (dateStr) => {
  if (!dateStr) return null;
  const diff = Date.now() - new Date(dateStr).getTime();
  return Math.floor(diff / 86_400_000);
};

// Risk % from entry to stop
const riskPct = (pos) => {
  if (!pos.entry_price || !pos.current_stop) return null;
  const dist = Math.abs(pos.entry_price - pos.current_stop);
  return (dist / pos.entry_price * 100).toFixed(2);
};

// R-distance: how far stop is from entry expressed as a ratio of the original risk
// We don't have initial stop, so we just show current stop-distance %.
const DirectionBadge = ({ state }) => {
  const isLong = state === 'LONG';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: isLong ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
      color: isLong ? '#10b981' : '#ef4444',
      fontWeight: 700, fontSize: 12, padding: '3px 10px', borderRadius: 6,
    }}>
      {isLong ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
      {state}
    </span>
  );
};

// ── Inline stop editor ────────────────────────────────────────────────────────

const StopEditor = ({ pos, onSaved, onCancel }) => {
  const { t } = useTranslation();
  const [val, setVal] = useState(pos.current_stop != null ? String(pos.current_stop) : '');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  const save = async () => {
    const n = parseFloat(val);
    if (!n || n <= 0) { setErr(t('decision_helper.positions.invalid_stop')); return; }
    setSaving(true);
    setErr(null);
    try {
      const updated = await helperService.updateStop(pos.ticker, n);
      onSaved(updated);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message || t('decision_helper.positions.stop_failed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr style={{ background: 'rgba(59,130,246,0.06)', borderBottom: '1px solid #1e3a5f' }}>
      <td colSpan={9} style={{ padding: '10px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <Shield size={14} color="#3b82f6" />
          <span style={{ fontSize: 13, color: '#93c5fd', fontWeight: 600 }}>
            {t('decision_helper.positions.update_stop_for', { ticker: pos.ticker })}
          </span>
          <input
            type="number"
            step="0.01"
            value={val}
            onChange={e => setVal(e.target.value)}
            autoFocus
            style={styles.stopInput}
          />
          <button onClick={save} disabled={saving} style={styles.saveBtn}>
            {saving ? <RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} /> : <Check size={12} />}
            {saving ? t('decision_helper.common.saving') : t('decision_helper.common.save')}
          </button>
          <button onClick={onCancel} style={styles.cancelBtn}><X size={12} /> {t('decision_helper.common.cancel')}</button>
          {err && <span style={{ color: '#f87171', fontSize: 12 }}>{err}</span>}
        </div>
      </td>
    </tr>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

const PositionsPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null);   // ticker being edited

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await helperService.getPositions();
      setPositions(data.positions ?? []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load positions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSaved = (updated) => {
    setPositions(prev => prev.map(p =>
      p.ticker === updated.ticker ? { ...p, current_stop: updated.current_stop } : p
    ));
    setEditing(null);
  };

  const longs = positions.filter(p => p.state === 'LONG').length;
  const shorts = positions.filter(p => p.state === 'SHORT').length;

  return (
    <div style={styles.page}>
      {/* ── Header ── */}
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Shield size={18} color="#a78bfa" />
          <span style={{ fontWeight: 700, fontSize: 16, color: '#f9fafb' }}>{t('decision_helper.positions.title')}</span>
          {positions.length > 0 && (
            <span style={styles.badge}>{t('decision_helper.positions.n_open', { count: positions.length })}</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {positions.length > 0 && (
            <div style={{ fontSize: 12, color: '#6b7280', display: 'flex', gap: 10 }}>
              <span style={{ color: '#10b981' }}>{longs} LONG</span>
              <span style={{ color: '#ef4444' }}>{shorts} SHORT</span>
            </div>
          )}
          <button onClick={load} disabled={loading} style={styles.refreshBtn}>
            <RefreshCw size={14}
              style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
          </button>
        </div>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {!loading && positions.length === 0 && !error && (
        <div style={styles.empty}>
          <Shield size={44} color="#374151" style={{ marginBottom: 12 }} />
          <div style={{ fontWeight: 600, color: '#6b7280', marginBottom: 4 }}>{t('decision_helper.positions.no_positions')}</div>
          <div style={{ fontSize: 13, color: '#4b5563' }}>{t('decision_helper.positions.no_positions_hint')}</div>
        </div>
      )}

      {positions.length > 0 && (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                {[t('decision_helper.positions.col_ticker'), t('decision_helper.positions.col_direction'), t('decision_helper.positions.col_entry_date'), t('decision_helper.positions.col_days'), t('decision_helper.positions.col_entry_price'), t('decision_helper.positions.col_stop'), t('decision_helper.positions.col_risk_pct'), t('decision_helper.positions.col_target'), t('decision_helper.positions.col_signal'), ''].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, i) => (
                <React.Fragment key={pos.ticker}>
                  <tr style={{ ...styles.tr, background: i % 2 === 0 ? '#111827' : 'transparent' }}>
                    {/* Ticker */}
                    <td style={{ ...styles.td, fontWeight: 800, fontSize: 14, color: '#f9fafb' }}>
                      <button
                        onClick={() => navigate(`/decision-console?ticker=${pos.ticker}`)}
                        style={styles.tickerBtn}
                        title={t('decision_helper.positions.analyze_hint')}
                      >
                        {pos.ticker}
                        <Zap size={10} color="#a78bfa" />
                      </button>
                    </td>
                    {/* Direction */}
                    <td style={styles.td}><DirectionBadge state={pos.state} /></td>
                    {/* Entry date */}
                    <td style={{ ...styles.td, color: '#9ca3af', fontSize: 12 }}>
                      {pos.entry_bar_date || '—'}
                    </td>
                    {/* Days held */}
                    <td style={{ ...styles.td, color: '#9ca3af' }}>
                      {daysSince(pos.entry_bar_date) != null
                        ? `${daysSince(pos.entry_bar_date)}d`
                        : '—'}
                    </td>
                    {/* Entry price */}
                    <td style={{ ...styles.td, fontWeight: 600 }}>{fmt(pos.entry_price)}</td>
                    {/* Current stop */}
                    <td style={{ ...styles.td, color: '#ef4444', fontWeight: 600 }}>
                      {fmt(pos.current_stop)}
                    </td>
                    {/* Risk % */}
                    <td style={{ ...styles.td, color: '#f59e0b' }}>
                      {riskPct(pos) != null ? `${riskPct(pos)}%` : '—'}
                    </td>
                    {/* Target */}
                    <td style={{ ...styles.td, color: '#10b981', fontWeight: 600 }}>
                      {fmt(pos.current_target)}
                    </td>
                    {/* Signal */}
                    <td style={{ ...styles.td, fontSize: 11, color: '#9ca3af' }}>
                      {pos.entry_signal_kind || '—'}
                    </td>
                    {/* Actions */}
                    <td style={styles.td}>
                      <button
                        onClick={() => setEditing(editing === pos.ticker ? null : pos.ticker)}
                        style={styles.editBtn}
                        title={t('decision_helper.positions.update_stop_hint')}
                      >
                        <Edit2 size={13} />
                      </button>
                    </td>
                  </tr>

                  {/* Inline stop editor */}
                  {editing === pos.ticker && (
                    <StopEditor
                      pos={pos}
                      onSaved={handleSaved}
                      onCancel={() => setEditing(null)}
                    />
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

const styles = {
  page: { padding: 20, maxWidth: 1100, margin: '0 auto', color: '#f9fafb' },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 16, flexWrap: 'wrap', gap: 10,
  },
  badge: {
    background: 'rgba(167,139,250,0.2)', color: '#a78bfa',
    fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
  },
  refreshBtn: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 7,
    padding: '7px 9px', color: '#9ca3af', cursor: 'pointer',
    display: 'flex', alignItems: 'center',
  },
  errorBanner: {
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 8, padding: '10px 14px', color: '#fca5a5',
    display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 12,
  },
  empty: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', minHeight: 220, textAlign: 'center',
  },
  tableWrap: { overflowX: 'auto', borderRadius: 10, border: '1px solid #374151' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: {
    background: '#111827', padding: '10px 12px', textAlign: 'left',
    color: '#9ca3af', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5,
    borderBottom: '1px solid #374151', whiteSpace: 'nowrap',
  },
  tr: { borderBottom: '1px solid #1f293730' },
  td: { padding: '11px 12px', verticalAlign: 'middle', whiteSpace: 'nowrap' },
  tickerBtn: {
    background: 'none', border: 'none', color: '#f9fafb', fontWeight: 800,
    fontSize: 14, cursor: 'pointer', display: 'inline-flex', alignItems: 'center',
    gap: 5, padding: 0,
  },
  editBtn: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 6,
    padding: '5px 7px', color: '#9ca3af', cursor: 'pointer',
    display: 'inline-flex', alignItems: 'center',
  },
  // Stop editor
  stopInput: {
    background: '#111827', border: '1px solid #3b82f6', borderRadius: 6,
    padding: '6px 10px', color: '#f9fafb', fontSize: 13, outline: 'none', width: 110,
  },
  saveBtn: {
    background: '#2563eb', border: 'none', borderRadius: 6,
    padding: '6px 14px', color: '#fff', fontWeight: 700, fontSize: 12,
    cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 5,
  },
  cancelBtn: {
    background: '#374151', border: 'none', borderRadius: 6,
    padding: '6px 12px', color: '#d1d5db', fontSize: 12,
    cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4,
  },
};

export default PositionsPage;
