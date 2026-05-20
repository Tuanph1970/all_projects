// F-161..F-163, F-190..F-193 — OutcomesPage: trade outcome log + AI post-mortem
import React, { useState, useEffect, useCallback } from 'react';
import helperService from '../../../services/helperService';

// ── Sub-components ──────────────────────────────────────────────────────────

const OutcomeBadge = ({ outcome }) => {
  const cfg = {
    WIN:       { bg: '#d1fae5', color: '#065f46', label: 'WIN' },
    LOSS:      { bg: '#fee2e2', color: '#991b1b', label: 'LOSS' },
    BREAKEVEN: { bg: '#fef9c3', color: '#92400e', label: 'EVEN' },
  }[outcome] || { bg: '#f3f4f6', color: '#374151', label: outcome || '—' };

  return (
    <span style={{
      background: cfg.bg,
      color: cfg.color,
      borderRadius: 4,
      padding: '2px 8px',
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: '0.05em',
    }}>
      {cfg.label}
    </span>
  );
};

const RBar = ({ r }) => {
  if (r == null) return <span style={{ color: '#9ca3af' }}>—</span>;
  const capped = Math.max(-3, Math.min(3, r));
  const pct = Math.abs(capped) / 3 * 100;
  const color = r > 0 ? '#10b981' : '#ef4444';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{
        width: 60, height: 8, background: '#e5e7eb', borderRadius: 4, overflow: 'hidden',
        position: 'relative',
      }}>
        <div style={{
          position: 'absolute',
          top: 0,
          left: r > 0 ? '50%' : `calc(50% - ${pct / 2}%)`,
          width: `${pct / 2}%`,
          height: '100%',
          background: color,
          borderRadius: 4,
        }} />
        <div style={{ position: 'absolute', left: '50%', top: 0, width: 1, height: '100%', background: '#9ca3af' }} />
      </div>
      <span style={{ fontSize: 12, color, fontWeight: 600, minWidth: 38 }}>
        {r > 0 ? '+' : ''}{r.toFixed(2)}R
      </span>
    </div>
  );
};

const SummaryCard = ({ label, value, sub, color }) => (
  <div style={{
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: 8,
    padding: '12px 16px',
    minWidth: 130,
    flex: 1,
  }}>
    <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 22, fontWeight: 700, color: color || '#111827' }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sub}</div>}
  </div>
);

// ── Main page ────────────────────────────────────────────────────────────────

// ── AI review panel ──────────────────────────────────────────────────────────

const ReviewPanel = ({ runId, cachedReview }) => {
  const [review, setReview] = useState(cachedReview || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await helperService.generateReview(runId);
      const d = res.data || res;
      setReview(d.ai_review || null);
      if (!d.ai_review) setError('AI review unavailable — check ai-insights-service.');
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to generate review');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (cachedReview) setReview(cachedReview);
  }, [cachedReview]);

  if (review) {
    return (
      <div style={{ padding: '10px 14px', background: '#f0f9ff', borderRadius: 6, fontSize: 12, color: '#1e40af', lineHeight: 1.6 }}>
        <span style={{ fontWeight: 700, color: '#1d4ed8', marginRight: 6 }}>AI Review:</span>
        {review}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <button
        onClick={generate}
        disabled={loading}
        style={{
          padding: '4px 12px', fontSize: 11, fontWeight: 600,
          background: loading ? '#e5e7eb' : '#dbeafe',
          color: loading ? '#9ca3af' : '#1d4ed8',
          border: '1px solid #bfdbfe', borderRadius: 5, cursor: loading ? 'not-allowed' : 'pointer',
        }}
      >{loading ? 'Generating…' : '✦ Generate AI Review'}</button>
      {error && <span style={{ fontSize: 11, color: '#ef4444' }}>{error}</span>}
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

const OutcomesPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(90);
  const [filter, setFilter] = useState('ALL');  // ALL | WIN | LOSS | BREAKEVEN
  const [expandedId, setExpandedId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await helperService.getOutcomes(days);
      setData(res.data || res);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load outcomes');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  const records = data?.records || [];
  const summary = data?.summary || {};

  const filtered = filter === 'ALL'
    ? records
    : records.filter(r => r.outcome === filter);

  const DAY_OPTS = [30, 60, 90, 180, 365];

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Trade Outcomes</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 13 }}>
            R-multiple log for closed positions
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {DAY_OPTS.map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={{
                padding: '4px 10px',
                border: '1px solid',
                borderColor: days === d ? '#6366f1' : '#d1d5db',
                borderRadius: 6,
                background: days === d ? '#6366f1' : '#fff',
                color: days === d ? '#fff' : '#374151',
                cursor: 'pointer',
                fontSize: 12,
                fontWeight: 600,
              }}
            >{d}d</button>
          ))}
          <button
            onClick={load}
            disabled={loading}
            style={{
              padding: '4px 12px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              background: '#f9fafb',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 12,
            }}
          >{loading ? '…' : '↻'}</button>
        </div>
      </div>

      {/* Summary cards */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <SummaryCard
          label="Tagged trades"
          value={summary.total_tagged ?? 0}
          sub={`last ${days} days`}
        />
        <SummaryCard
          label="Win rate"
          value={summary.total_tagged ? `${(summary.win_rate * 100).toFixed(1)}%` : '—'}
          sub={`${summary.wins ?? 0}W / ${summary.losses ?? 0}L / ${summary.breakevens ?? 0}E`}
          color={summary.win_rate >= 0.5 ? '#10b981' : '#ef4444'}
        />
        <SummaryCard
          label="Avg R"
          value={summary.avg_r != null ? (summary.avg_r > 0 ? '+' : '') + summary.avg_r.toFixed(2) + 'R' : '—'}
          color={summary.avg_r > 0 ? '#10b981' : summary.avg_r < 0 ? '#ef4444' : '#111827'}
        />
        <SummaryCard
          label="Expectancy"
          value={summary.expectancy != null ? (summary.expectancy > 0 ? '+' : '') + summary.expectancy.toFixed(2) + 'R' : '—'}
          sub="per trade"
          color={summary.expectancy > 0 ? '#10b981' : summary.expectancy < 0 ? '#ef4444' : '#111827'}
        />
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
        {['ALL', 'WIN', 'LOSS', 'BREAKEVEN'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '4px 12px',
              borderRadius: 6,
              border: '1px solid',
              borderColor: filter === f ? '#6366f1' : '#e5e7eb',
              background: filter === f ? '#eef2ff' : '#fff',
              color: filter === f ? '#4338ca' : '#374151',
              fontWeight: filter === f ? 700 : 400,
              cursor: 'pointer',
              fontSize: 12,
            }}
          >{f}{f === 'ALL' ? ` (${records.length})` : ` (${records.filter(r => r.outcome === f).length})`}</button>
        ))}
      </div>

      {/* Error / empty */}
      {error && (
        <div style={{ padding: 16, background: '#fee2e2', borderRadius: 8, color: '#991b1b', marginBottom: 16 }}>
          {error}
        </div>
      )}

      {!loading && !error && records.length === 0 && (
        <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
          No tagged outcomes yet. Outcomes are recorded automatically when a SELL/COVER/REVERSE decision closes a position.
        </div>
      )}

      {/* Table */}
      {filtered.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                {['Ticker', 'Entry date', 'Action', 'Outcome', 'R-multiple', 'Entry', 'Stop', 'Exit', 'Signal', 'Regime', 'AI'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(rec => {
                const isExpanded = expandedId === rec.run_id;
                return (
                  <React.Fragment key={rec.run_id}>
                    <tr style={{ borderBottom: isExpanded ? 'none' : '1px solid #f3f4f6', background: isExpanded ? '#fafafa' : undefined }}>
                      <td style={{ padding: '8px 12px', fontWeight: 700 }}>
                        <button
                          onClick={() => window.location.href = `/decision-console?ticker=${rec.ticker}`}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#4f46e5', fontWeight: 700, fontSize: 13 }}
                        >{rec.ticker}</button>
                      </td>
                      <td style={{ padding: '8px 12px', color: '#6b7280' }}>{rec.bar_date}</td>
                      <td style={{ padding: '8px 12px' }}>
                        <span style={{
                          background: rec.action === 'BUY' ? '#d1fae5' : '#fee2e2',
                          color: rec.action === 'BUY' ? '#065f46' : '#991b1b',
                          borderRadius: 4, padding: '2px 6px', fontSize: 11, fontWeight: 700,
                        }}>{rec.action}</span>
                      </td>
                      <td style={{ padding: '8px 12px' }}><OutcomeBadge outcome={rec.outcome} /></td>
                      <td style={{ padding: '8px 12px' }}><RBar r={rec.r_multiple} /></td>
                      <td style={{ padding: '8px 12px', color: '#374151' }}>{rec.entry_price?.toFixed(2) ?? '—'}</td>
                      <td style={{ padding: '8px 12px', color: '#374151' }}>{rec.stop_price?.toFixed(2) ?? '—'}</td>
                      <td style={{ padding: '8px 12px', fontWeight: 600 }}>{rec.exit_price?.toFixed(2) ?? '—'}</td>
                      <td style={{ padding: '8px 12px', color: '#6b7280', fontSize: 11 }}>{rec.signal_kind ?? '—'}</td>
                      <td style={{ padding: '8px 12px', color: '#6b7280', fontSize: 11 }}>{rec.regime ?? '—'}</td>
                      <td style={{ padding: '8px 12px' }}>
                        {rec.outcome && (
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : rec.run_id)}
                            style={{
                              padding: '2px 8px', fontSize: 11, fontWeight: 600,
                              background: isExpanded ? '#dbeafe' : (rec.ai_review ? '#f0f9ff' : '#f9fafb'),
                              color: isExpanded ? '#1d4ed8' : '#6b7280',
                              border: '1px solid',
                              borderColor: isExpanded ? '#bfdbfe' : '#e5e7eb',
                              borderRadius: 5, cursor: 'pointer',
                            }}
                          >{isExpanded ? '▲ Close' : (rec.ai_review ? '✦ View' : '✦ AI')}</button>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr style={{ borderBottom: '1px solid #f3f4f6', background: '#fafafa' }}>
                        <td colSpan={11} style={{ padding: '0 12px 12px 12px' }}>
                          <ReviewPanel runId={rec.run_id} cachedReview={rec.ai_review} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {loading && (
        <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>Loading…</div>
      )}
    </div>
  );
};

export default OutcomesPage;
