// F-161..F-163, F-190..F-193, F-210..F-213 — OutcomesPage: trade outcome log + AI review + attribution
import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();
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
      if (!d.ai_review) setError(t('decision_helper.outcomes.ai_unavailable'));
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || t('decision_helper.outcomes.ai_failed'));
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
        <span style={{ fontWeight: 700, color: '#1d4ed8', marginRight: 6 }}>{t('decision_helper.outcomes.ai_review_label')}</span>
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
      >{loading ? t('decision_helper.outcomes.generating_ai') : t('decision_helper.outcomes.generate_ai')}</button>
      {error && <span style={{ fontSize: 11, color: '#ef4444' }}>{error}</span>}
    </div>
  );
};

// ── Attribution view (F-210..F-213) ──────────────────────────────────────────

const winRateColor = (wr) => {
  if (wr == null) return '#6b7280';
  if (wr >= 0.6) return '#10b981';
  if (wr >= 0.45) return '#f59e0b';
  return '#ef4444';
};

const AttributionTable = ({ title, rows }) => {
  const { t } = useTranslation();
  if (!rows || rows.length === 0) return null;
  const maxCount = Math.max(...rows.map(r => r.count), 1);
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '14px 18px', marginBottom: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#374151', marginBottom: 10 }}>{title}</div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #f3f4f6' }}>
            {[t('decision_helper.outcomes.attr_col_category'), t('decision_helper.outcomes.attr_col_trades'), t('decision_helper.outcomes.attr_col_win_pct'), t('decision_helper.outcomes.attr_col_avg_r'), t('decision_helper.outcomes.attr_col_expectancy'), ''].map(h => (
              <th key={h} style={{ padding: '4px 10px', textAlign: h === '' ? 'left' : 'right', color: '#6b7280', fontWeight: 600, whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            const barW = Math.round(row.count / maxCount * 100);
            const wr = row.win_rate;
            return (
              <tr key={row.label} style={{ borderBottom: '1px solid #f9fafb' }}>
                <td style={{ padding: '5px 10px', fontWeight: 600 }}>{row.label}</td>
                <td style={{ padding: '5px 10px', textAlign: 'right', color: '#374151' }}>{row.count}</td>
                <td style={{ padding: '5px 10px', textAlign: 'right', fontWeight: 700, color: winRateColor(wr) }}>
                  {row.count > 0 ? `${(wr * 100).toFixed(1)}%` : '—'}
                </td>
                <td style={{ padding: '5px 10px', textAlign: 'right', color: row.avg_r > 0 ? '#10b981' : row.avg_r < 0 ? '#ef4444' : '#6b7280' }}>
                  {row.avg_r != null ? `${row.avg_r > 0 ? '+' : ''}${row.avg_r.toFixed(2)}R` : '—'}
                </td>
                <td style={{ padding: '5px 10px', textAlign: 'right', color: row.expectancy > 0 ? '#10b981' : row.expectancy < 0 ? '#ef4444' : '#6b7280' }}>
                  {row.expectancy != null ? `${row.expectancy > 0 ? '+' : ''}${row.expectancy.toFixed(2)}R` : '—'}
                </td>
                <td style={{ padding: '5px 10px', minWidth: 80 }}>
                  <div style={{ height: 6, background: '#f3f4f6', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${barW}%`, height: '100%', background: winRateColor(wr), borderRadius: 3 }} />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const AttributionView = ({ days }) => {
  const { t } = useTranslation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    helperService.getAttribution(days)
      .then(res => setData(res.data || res))
      .catch(err => setError(err?.response?.data?.detail || err.message || 'Failed to load attribution'))
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>{t('decision_helper.outcomes.attr_loading')}</div>;
  if (error) return <div style={{ padding: 16, background: '#fee2e2', borderRadius: 8, color: '#991b1b' }}>{error}</div>;
  if (!data || data.total_tagged === 0) return (
    <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
      {t('decision_helper.outcomes.attr_no_data')}
    </div>
  );

  return (
    <div>
      <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 14 }}>
        {t('decision_helper.outcomes.attr_tagged', { count: data.total_tagged, days })}
      </div>
      <AttributionTable title={t('decision_helper.outcomes.attr_by_signal')} rows={data.by_signal} />
      <AttributionTable title={t('decision_helper.outcomes.attr_by_regime')} rows={data.by_regime} />
      <AttributionTable title={t('decision_helper.outcomes.attr_by_weekday')} rows={data.by_weekday} />
      <AttributionTable title={t('decision_helper.outcomes.attr_by_hold')} rows={data.by_hold_duration} />
    </div>
  );
};


// ── Main page ─────────────────────────────────────────────────────────────────

const OutcomesPage = () => {
  const { t } = useTranslation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(90);
  const [filter, setFilter] = useState('ALL');  // ALL | WIN | LOSS | BREAKEVEN
  const [expandedId, setExpandedId] = useState(null);
  const [view, setView] = useState('log');      // 'log' | 'attribution'

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
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>{t('decision_helper.outcomes.title')}</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 13 }}>
            {t('decision_helper.outcomes.subtitle')}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {/* View toggle */}
          {['log', 'attribution'].map(v => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                padding: '4px 11px', border: '1px solid',
                borderColor: view === v ? '#6366f1' : '#e5e7eb',
                borderRadius: 6,
                background: view === v ? '#eef2ff' : '#fff',
                color: view === v ? '#4338ca' : '#374151',
                fontWeight: view === v ? 700 : 400,
                cursor: 'pointer', fontSize: 12,
              }}
            >{v === 'log' ? t('decision_helper.outcomes.view_log') : t('decision_helper.outcomes.view_attribution')}</button>
          ))}
          <div style={{ width: 1, height: 20, background: '#e5e7eb', margin: '0 4px' }} />
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
          label={t('decision_helper.outcomes.tagged_trades')}
          value={summary.total_tagged ?? 0}
          sub={t('decision_helper.outcomes.last_n_days', { n: days })}
        />
        <SummaryCard
          label={t('decision_helper.outcomes.win_rate')}
          value={summary.total_tagged ? `${(summary.win_rate * 100).toFixed(1)}%` : '—'}
          sub={t('decision_helper.outcomes.wl_summary', { wins: summary.wins ?? 0, losses: summary.losses ?? 0, breakevens: summary.breakevens ?? 0 })}
          color={summary.win_rate >= 0.5 ? '#10b981' : '#ef4444'}
        />
        <SummaryCard
          label={t('decision_helper.outcomes.avg_r')}
          value={summary.avg_r != null ? (summary.avg_r > 0 ? '+' : '') + summary.avg_r.toFixed(2) + 'R' : '—'}
          color={summary.avg_r > 0 ? '#10b981' : summary.avg_r < 0 ? '#ef4444' : '#111827'}
        />
        <SummaryCard
          label={t('decision_helper.outcomes.expectancy')}
          value={summary.expectancy != null ? (summary.expectancy > 0 ? '+' : '') + summary.expectancy.toFixed(2) + 'R' : '—'}
          sub={t('decision_helper.outcomes.per_trade')}
          color={summary.expectancy > 0 ? '#10b981' : summary.expectancy < 0 ? '#ef4444' : '#111827'}
        />
      </div>

      {/* Attribution view */}
      {view === 'attribution' && <AttributionView days={days} />}

      {/* Log view */}
      {view === 'log' && <>

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
          {t('decision_helper.outcomes.no_outcomes')}
        </div>
      )}

      {/* Table */}
      {filtered.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                {[t('decision_helper.outcomes.col_ticker'), t('decision_helper.outcomes.col_entry_date'), t('decision_helper.outcomes.col_action'), t('decision_helper.outcomes.col_outcome'), t('decision_helper.outcomes.col_r'), t('decision_helper.outcomes.col_entry'), t('decision_helper.outcomes.col_stop'), t('decision_helper.outcomes.col_exit'), t('decision_helper.outcomes.col_signal'), t('decision_helper.outcomes.col_regime'), t('decision_helper.outcomes.col_ai')].map(h => (
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
                          >{isExpanded ? t('decision_helper.outcomes.view_close') : (rec.ai_review ? '✦ View' : '✦ AI')}</button>
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
        <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>{t('decision_helper.common.loading')}</div>
      )}

      </>}
    </div>
  );
};

export default OutcomesPage;
