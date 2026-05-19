// F-073 — ScheduledRunsLog (Phase H)
// Watchlist manager + table of recent scheduled recommendation runs
import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock, Plus, Trash2, Play, AlertTriangle, RefreshCw,
  CheckCircle, Bell, BellOff,
} from 'lucide-react';
import helperService from '../../../services/helperService';

// ── helpers ──────────────────────────────────────────────────────────────────

const ACTION_COLOR = {
  BUY:        '#10b981',
  SELL_SHORT: '#f59e0b',
  SELL:       '#ef4444',
  COVER:      '#3b82f6',
  HOLD:       '#8b5cf6',
  WAIT:       '#6b7280',
  REVERSE:    '#8b5cf6',
};

const fmt = (v) => v != null ? `${(v * 100).toFixed(0)}%` : '—';

const fmtDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

const fmtTs = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
};

// ── sub-components ────────────────────────────────────────────────────────────

const ActionBadge = ({ action }) => {
  const color = ACTION_COLOR[action] || '#6b7280';
  return (
    <span style={{
      padding: '2px 10px', borderRadius: 6, fontSize: 11, fontWeight: 700,
      background: color + '22', color, border: `1px solid ${color}44`,
    }}>
      {action}
    </span>
  );
};

const AlertDot = ({ isAlert }) => isAlert ? (
  <Bell size={13} color="#f59e0b" title="Alert — actionable signal" />
) : (
  <BellOff size={13} color="#374151" title="No action required" />
);

// ── WatchlistPanel ────────────────────────────────────────────────────────────

const WatchlistPanel = ({ onRunAll, running }) => {
  const [entries, setEntries] = useState([]);
  const [tickerInput, setTickerInput] = useState('');
  const [noteInput, setNoteInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await helperService.getWatchlist();
      setEntries(data);
    } catch { /* watchlist empty or not authenticated — no-op */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    const ticker = tickerInput.trim().toUpperCase();
    if (!ticker) return;
    setBusy(true);
    setErr(null);
    try {
      await helperService.addWatchlist({ ticker, note: noteInput.trim() || undefined });
      setTickerInput('');
      setNoteInput('');
      await load();
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (ticker) => {
    setBusy(true);
    try {
      await helperService.removeWatchlist(ticker);
      await load();
    } catch { /* ignore */ } finally {
      setBusy(false);
    }
  };

  return (
    <div style={s.panel}>
      <div style={s.panelTitle}>
        <Clock size={14} color="#a78bfa" /> Watchlist ({entries.length} tickers)
      </div>

      {/* Add row */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <input
          value={tickerInput}
          onChange={e => setTickerInput(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
          placeholder="Ticker"
          style={s.tickerInput}
        />
        <input
          value={noteInput}
          onChange={e => setNoteInput(e.target.value)}
          placeholder="Note (optional)"
          style={{ ...s.tickerInput, flex: 1, minWidth: 120 }}
        />
        <button onClick={handleAdd} disabled={busy || !tickerInput.trim()} style={s.addBtn}>
          <Plus size={14} /> Add
        </button>
        <button onClick={onRunAll} disabled={running} style={s.runBtn}>
          {running
            ? <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />
            : <Play size={14} />}
          {running ? 'Running…' : 'Run All Now'}
        </button>
      </div>

      {err && (
        <div style={{ color: '#fca5a5', fontSize: 12, marginBottom: 8 }}>
          <AlertTriangle size={12} /> {err}
        </div>
      )}

      {entries.length === 0 ? (
        <div style={{ color: '#6b7280', fontSize: 13, textAlign: 'center', padding: 16 }}>
          No tickers in watchlist. Add tickers above to enable daily recommendations.
        </div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {entries.map(e => (
            <div key={e.ticker} style={s.chip}>
              <span style={{ fontWeight: 700, fontSize: 12, color: '#f9fafb' }}>{e.ticker}</span>
              {e.note && <span style={{ fontSize: 10, color: '#6b7280', marginLeft: 4 }}>{e.note}</span>}
              <button
                onClick={() => handleRemove(e.ticker)}
                style={s.removeBtn}
                title={`Remove ${e.ticker}`}
              >
                <Trash2 size={10} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ── RunsTable ─────────────────────────────────────────────────────────────────

const RunsTable = ({ runs }) => {
  if (runs.length === 0) {
    return (
      <div style={{ color: '#6b7280', textAlign: 'center', padding: 32, fontSize: 13 }}>
        No scheduled runs yet. Add tickers to your watchlist and click "Run All Now", or wait for the
        daily 15:30 ICT automatic run.
      </div>
    );
  }

  return (
    <table style={s.table}>
      <thead>
        <tr>
          {['Alert', 'Ticker', 'Bar Date', 'Action', 'Regime', 'Confidence', 'Latency', 'Run At'].map(h => (
            <th key={h} style={s.th}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {runs.map(r => (
          <tr key={r.id} style={{ borderBottom: '1px solid #1f2937' }}>
            <td style={s.td}><AlertDot isAlert={r.is_alert} /></td>
            <td style={{ ...s.td, fontWeight: 700, color: '#f9fafb' }}>{r.ticker}</td>
            <td style={s.td}>{fmtDate(r.bar_date)}</td>
            <td style={s.td}><ActionBadge action={r.action} /></td>
            <td style={s.td}>{r.regime || '—'}</td>
            <td style={s.td}>{fmt(r.confidence)}</td>
            <td style={s.td}>{r.latency_ms != null ? `${r.latency_ms}ms` : '—'}</td>
            <td style={s.td}>{fmtTs(r.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

// ── main page ─────────────────────────────────────────────────────────────────

const ScheduledRunsLog = () => {
  const [runs, setRuns] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [alertsOnly, setAlertsOnly] = useState(false);
  const [error, setError] = useState(null);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await helperService.getScheduledRuns({ limit: 100, alertsOnly });
      setRuns(data.runs || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load scheduled runs');
    } finally {
      setLoading(false);
    }
  }, [alertsOnly]);

  useEffect(() => { loadRuns(); }, [loadRuns]);

  const handleRunAll = async () => {
    setRunning(true);
    try {
      await helperService.triggerScheduledRun();
      setTimeout(loadRuns, 3000);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to trigger run');
    } finally {
      setRunning(false);
    }
  };

  const alertCount = runs.filter(r => r.is_alert).length;

  return (
    <div style={s.page}>
      {/* ── header ── */}
      <div style={s.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Clock size={22} color="#a78bfa" />
          <span style={{ fontSize: 20, fontWeight: 800, color: '#f9fafb' }}>Scheduled Runs</span>
          {alertCount > 0 && (
            <span style={s.alertBadge}>{alertCount} alert{alertCount > 1 ? 's' : ''}</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            onClick={() => setAlertsOnly(v => !v)}
            style={{ ...s.filterBtn, background: alertsOnly ? 'rgba(245,158,11,0.2)' : '#1f2937', color: alertsOnly ? '#f59e0b' : '#9ca3af', borderColor: alertsOnly ? '#f59e0b44' : '#374151' }}
          >
            <Bell size={13} /> {alertsOnly ? 'Alerts only' : 'All runs'}
          </button>
          <button onClick={loadRuns} disabled={loading} style={s.refreshBtn}>
            <RefreshCw size={13} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div style={s.errorBanner}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* ── watchlist panel ── */}
      <WatchlistPanel onRunAll={handleRunAll} running={running} />

      {/* ── runs log ── */}
      <div style={s.section}>
        <div style={s.sectionTitle}>
          <CheckCircle size={14} color="#10b981" />
          Recent Scheduled Runs
          {total > 0 && <span style={{ color: '#6b7280', fontWeight: 400 }}>({total} total)</span>}
        </div>
        <RunsTable runs={runs} />
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

const s = {
  page: { padding: 20, maxWidth: 960, margin: '0 auto', color: '#f9fafb' },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20,
  },
  alertBadge: {
    background: 'rgba(245,158,11,0.2)', color: '#f59e0b',
    border: '1px solid rgba(245,158,11,0.4)',
    borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700,
  },
  filterBtn: {
    border: '1px solid', borderRadius: 8, padding: '6px 12px',
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5, fontSize: 12,
  },
  refreshBtn: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 8,
    padding: '6px 12px', color: '#9ca3af', cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 5, fontSize: 12,
  },
  errorBanner: {
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 8, padding: '10px 14px', color: '#fca5a5',
    display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 14,
  },
  panel: {
    background: '#1f2937', borderRadius: 10, border: '1px solid #374151',
    padding: 16, marginBottom: 16,
  },
  panelTitle: {
    fontSize: 13, fontWeight: 700, color: '#d1d5db',
    marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6,
  },
  tickerInput: {
    background: '#111827', border: '1px solid #374151', borderRadius: 8,
    padding: '7px 12px', color: '#f9fafb', fontSize: 13, outline: 'none',
    width: 90, textTransform: 'uppercase',
  },
  addBtn: {
    background: '#374151', border: 'none', borderRadius: 8,
    padding: '7px 14px', color: '#d1d5db', cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 5, fontSize: 13,
  },
  runBtn: {
    background: '#a78bfa', border: 'none', borderRadius: 8,
    padding: '7px 14px', color: '#fff', fontWeight: 600, cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 5, fontSize: 13,
  },
  chip: {
    background: '#111827', border: '1px solid #374151', borderRadius: 8,
    padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 6,
  },
  removeBtn: {
    background: 'none', border: 'none', color: '#6b7280',
    cursor: 'pointer', padding: 2, display: 'flex', alignItems: 'center',
  },
  section: {
    background: '#1f2937', borderRadius: 10, border: '1px solid #374151',
    padding: 16,
  },
  sectionTitle: {
    fontSize: 13, fontWeight: 700, color: '#d1d5db',
    marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6,
  },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: {
    textAlign: 'left', color: '#6b7280', fontWeight: 600,
    padding: '6px 10px', borderBottom: '1px solid #374151', fontSize: 11,
    textTransform: 'uppercase', letterSpacing: 0.5,
  },
  td: { padding: '8px 10px', color: '#9ca3af', verticalAlign: 'middle' },
};

export default ScheduledRunsLog;
