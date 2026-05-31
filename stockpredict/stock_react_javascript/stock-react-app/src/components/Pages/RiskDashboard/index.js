// F-181..F-183, F-200..F-203 — RiskDashboard: portfolio-level risk overview + correlation matrix
import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import helperService from '../../../services/helperService';

// ── Utility ──────────────────────────────────────────────────────────────────

const fmt = (n, dec = 2) =>
  n == null ? '—' : Number(n).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });

const pctColor = (pct) => {
  if (pct == null) return '#6b7280';
  if (pct >= 5) return '#ef4444';
  if (pct >= 2) return '#f59e0b';
  return '#10b981';
};

// ── Sub-components ────────────────────────────────────────────────────────────

const SummaryCard = ({ label, value, sub, color, bg }) => (
  <div style={{
    background: bg || '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: 10,
    padding: '14px 18px',
    flex: 1,
    minWidth: 140,
  }}>
    <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>{label}</div>
    <div style={{ fontSize: 24, fontWeight: 800, color: color || '#111827' }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 3 }}>{sub}</div>}
  </div>
);

const ExposureBar = ({ label, pct, amount, direction, maxPct }) => {
  const barPct = maxPct > 0 ? Math.min(pct / maxPct * 100, 100) : 0;
  const color = direction === 'LONG' ? '#10b981' : '#ef4444';
  const warnColor = pct >= 5 ? '#ef4444' : pct >= 2 ? '#f59e0b' : color;
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            background: direction === 'LONG' ? '#d1fae5' : '#fee2e2',
            color: direction === 'LONG' ? '#065f46' : '#991b1b',
            fontSize: 10, fontWeight: 700, padding: '1px 5px', borderRadius: 3,
          }}>{direction}</span>
          <span style={{ fontWeight: 700, fontSize: 13 }}>{label}</span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontWeight: 700, fontSize: 13, color: warnColor }}>{fmt(pct, 2)}%</span>
          <span style={{ fontSize: 11, color: '#9ca3af', marginLeft: 6 }}>{fmt(amount, 0)} VND</span>
        </div>
      </div>
      <div style={{ height: 8, background: '#f3f4f6', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          width: `${barPct}%`,
          height: '100%',
          background: warnColor,
          borderRadius: 4,
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  );
};

const LongShortGauge = ({ longPct, shortPct }) => {
  const { t } = useTranslation();
  const total = longPct + shortPct || 1;
  const longW = Math.round(longPct / total * 100);
  const shortW = 100 - longW;
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '14px 18px' }}>
      <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10, color: '#374151' }}>{t('decision_helper.risk.long_short_split')}</div>
      <div style={{ display: 'flex', height: 20, borderRadius: 6, overflow: 'hidden', marginBottom: 8 }}>
        <div style={{ width: `${longW}%`, background: '#10b981', transition: 'width 0.4s' }} />
        <div style={{ width: `${shortW}%`, background: '#ef4444', transition: 'width 0.4s' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
        <span style={{ color: '#10b981', fontWeight: 700 }}>Long {fmt(longPct)}%</span>
        <span style={{ color: '#ef4444', fontWeight: 700 }}>Short {fmt(shortPct)}%</span>
      </div>
    </div>
  );
};

const DrawdownCard = ({ scenario, pct, equity }) => {
  const { t } = useTranslation();
  const critical = pct >= 5;
  return (
    <div style={{
      background: critical ? '#fff1f2' : '#f0fdf4',
      border: `1px solid ${critical ? '#fecdd3' : '#bbf7d0'}`,
      borderRadius: 10,
      padding: '14px 18px',
    }}>
      <div style={{ fontSize: 11, color: critical ? '#991b1b' : '#065f46', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
        {t('decision_helper.risk.worst_case')}
      </div>
      <div style={{ fontSize: 24, fontWeight: 800, color: critical ? '#dc2626' : '#059669' }}>
        −{fmt(scenario, 0)} VND
      </div>
      <div style={{ fontSize: 12, color: '#6b7280', marginTop: 3 }}>
        {equity ? t('decision_helper.risk.drawdown_pct_equity', { pct: fmt(pct), equity: fmt(equity, 0) }) : t('decision_helper.risk.drawdown_pct_no_equity', { pct: fmt(pct) })}
      </div>
    </div>
  );
};

const PositionTable = ({ positions }) => {
  const { t } = useTranslation();
  if (!positions?.length) return null;
  return (
    <div style={{ overflowX: 'auto', marginTop: 20 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#374151', marginBottom: 10 }}>{t('decision_helper.risk.position_detail')}</div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
            {[t('decision_helper.risk.col_ticker'), t('decision_helper.risk.col_direction'), t('decision_helper.risk.col_entry'), t('decision_helper.risk.col_stop'), t('decision_helper.risk.col_shares'), t('decision_helper.risk.col_risk_per_share'), t('decision_helper.risk.col_risk_amount'), t('decision_helper.risk.col_equity_pct'), t('decision_helper.risk.col_days')].map(h => (
              <th key={h} style={{ padding: '7px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map(p => (
            <tr key={p.ticker} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '7px 12px', fontWeight: 700 }}>
                <button
                  onClick={() => window.location.href = `/decision-console?ticker=${p.ticker}`}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#4f46e5', fontWeight: 700, fontSize: 12 }}
                >{p.ticker}</button>
              </td>
              <td style={{ padding: '7px 12px' }}>
                <span style={{
                  background: p.direction === 'LONG' ? '#d1fae5' : '#fee2e2',
                  color: p.direction === 'LONG' ? '#065f46' : '#991b1b',
                  fontSize: 10, fontWeight: 700, padding: '1px 5px', borderRadius: 3,
                }}>{p.direction}</span>
              </td>
              <td style={{ padding: '7px 12px', color: '#374151' }}>{fmt(p.entry_price)}</td>
              <td style={{ padding: '7px 12px', color: '#6b7280' }}>{fmt(p.current_stop)}</td>
              <td style={{ padding: '7px 12px', color: '#374151' }}>{p.position_size?.toLocaleString() ?? '—'}</td>
              <td style={{ padding: '7px 12px', color: '#374151' }}>{fmt(p.risk_per_share)}</td>
              <td style={{ padding: '7px 12px', fontWeight: 600 }}>{fmt(p.risk_amount, 0)}</td>
              <td style={{ padding: '7px 12px', color: pctColor(p.risk_pct_equity), fontWeight: 700 }}>
                {fmt(p.risk_pct_equity)}%
              </td>
              <td style={{ padding: '7px 12px', color: '#6b7280' }}>{p.days_held ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

// ── Correlation matrix panel (F-200..F-203) ──────────────────────────────────

const corrColor = (r) => {
  if (r == null) return '#f3f4f6';
  const abs = Math.abs(r);
  if (abs >= 0.8) return r > 0 ? '#fca5a5' : '#a5b4fc';
  if (abs >= 0.6) return r > 0 ? '#fcd34d' : '#c4b5fd';
  if (abs >= 0.4) return r > 0 ? '#fef9c3' : '#e0e7ff';
  return '#f9fafb';
};

const CorrelationMatrix = ({ tickers, pairs, maxCorrelation, anyBreach }) => {
  const { t } = useTranslation();
  if (!tickers || tickers.length < 2) return null;

  const lookup = {};
  pairs.forEach(p => {
    lookup[`${p.ticker_a}|${p.ticker_b}`] = p;
    lookup[`${p.ticker_b}|${p.ticker_a}`] = p;
  });

  return (
    <div style={{ background: '#fff', border: `1px solid ${anyBreach ? '#fca5a5' : '#e5e7eb'}`, borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#374151' }}>
          {t('decision_helper.risk.correlation_title')}
          {anyBreach && (
            <span style={{ marginLeft: 10, fontSize: 11, background: '#fee2e2', color: '#991b1b', padding: '2px 7px', borderRadius: 4, fontWeight: 700 }}>
              {t('decision_helper.risk.limit_breach')}
            </span>
          )}
        </div>
        <span style={{ fontSize: 11, color: '#9ca3af' }}>{t('decision_helper.risk.corr_limit', { n: (maxCorrelation * 100).toFixed(0) })}</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{ padding: '4px 10px', textAlign: 'left', color: '#6b7280' }}></th>
              {tickers.map(t => (
                <th key={t} style={{ padding: '4px 10px', fontWeight: 700, color: '#374151', textAlign: 'center' }}>{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tickers.map(rowT => (
              <tr key={rowT}>
                <td style={{ padding: '4px 10px', fontWeight: 700, color: '#374151', whiteSpace: 'nowrap' }}>{rowT}</td>
                {tickers.map(colT => {
                  if (rowT === colT) {
                    return (
                      <td key={colT} style={{ padding: '4px 10px', textAlign: 'center', background: '#f3f4f6', color: '#6b7280', borderRadius: 4 }}>1.00</td>
                    );
                  }
                  const pair = lookup[`${rowT}|${colT}`];
                  const r = pair?.correlation;
                  const breach = pair?.breaches_limit;
                  return (
                    <td key={colT} style={{
                      padding: '4px 10px', textAlign: 'center',
                      background: corrColor(r),
                      borderRadius: 4,
                      fontWeight: breach ? 700 : 400,
                      color: breach ? '#991b1b' : '#374151',
                      outline: breach ? '1px solid #ef4444' : 'none',
                    }}>
                      {r != null ? r.toFixed(2) : '—'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 8, fontSize: 11, color: '#9ca3af' }}>
        {t('decision_helper.risk.color_scale')}
      </div>
    </div>
  );
};


const RiskDashboard = () => {
  const { t } = useTranslation();
  const [data, setData] = useState(null);
  const [corrData, setCorrData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [riskRes, corrRes] = await Promise.allSettled([
        helperService.getRiskOverview(),
        helperService.getCorrelation(),
      ]);
      if (riskRes.status === 'fulfilled') setData(riskRes.value.data || riskRes.value);
      if (corrRes.status === 'fulfilled') setCorrData(corrRes.value.data || corrRes.value);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load risk overview');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const positions = data?.positions || [];
  const maxRiskPct = positions.length
    ? Math.max(...positions.map(p => p.risk_pct_equity || 0), 0.1)
    : 1;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>{t('decision_helper.risk.title')}</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 13 }}>
            {t('decision_helper.risk.subtitle')}
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          style={{
            padding: '6px 14px', border: '1px solid #d1d5db', borderRadius: 6,
            background: '#f9fafb', cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12,
          }}
        >{loading ? '…' : `↻ ${t('decision_helper.common.refresh')}`}</button>
      </div>

      {error && (
        <div style={{ padding: 16, background: '#fee2e2', borderRadius: 8, color: '#991b1b', marginBottom: 16 }}>
          {error}
        </div>
      )}

      {loading && !data && (
        <div style={{ padding: 60, textAlign: 'center', color: '#6b7280' }}>{t('decision_helper.common.loading')}</div>
      )}

      {data && (
        <>
          {/* Summary cards */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
            <SummaryCard
              label={t('decision_helper.risk.open_positions')}
              value={data.total_positions}
              sub={t('decision_helper.risk.long_short_count', { long: data.long_count, short: data.short_count })}
            />
            <SummaryCard
              label={t('decision_helper.risk.total_risk_pct')}
              value={`${fmt(data.total_risk_pct)}%`}
              sub={t('decision_helper.risk.vnd_at_risk', { amount: fmt(data.total_risk_amount, 0) })}
              color={pctColor(data.total_risk_pct)}
            />
            <SummaryCard
              label={t('decision_helper.risk.net_exposure')}
              value={`${data.net_exposure_pct >= 0 ? '+' : ''}${fmt(data.net_exposure_pct)}%`}
              sub={data.net_exposure_pct >= 0 ? t('decision_helper.risk.net_long_bias') : t('decision_helper.risk.net_short_bias')}
              color={data.net_exposure_pct >= 0 ? '#10b981' : '#ef4444'}
            />
            <SummaryCard
              label={t('decision_helper.risk.account_equity')}
              value={data.account_equity ? `${fmt(data.account_equity, 0)}` : '—'}
              sub={t('decision_helper.risk.vnd')}
            />
          </div>

          {/* Drawdown + gauge */}
          <div className="responsive-stack" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
            <DrawdownCard
              scenario={data.max_drawdown_scenario}
              pct={data.max_drawdown_pct}
              equity={data.account_equity}
            />
            <LongShortGauge
              longPct={data.long_risk_pct}
              shortPct={data.short_risk_pct}
            />
          </div>

          {/* Per-position exposure bars */}
          {positions.length > 0 && (
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#374151', marginBottom: 14 }}>
                {t('decision_helper.risk.position_detail')}
              </div>
              {positions.map(p => (
                <ExposureBar
                  key={p.ticker}
                  label={p.ticker}
                  pct={p.risk_pct_equity || 0}
                  amount={p.risk_amount || 0}
                  direction={p.direction}
                  maxPct={maxRiskPct}
                />
              ))}
            </div>
          )}

          {positions.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
              {t('decision_helper.risk.no_positions')}
            </div>
          )}

          {/* Correlation matrix (F-200) */}
          {corrData && corrData.tickers && corrData.tickers.length >= 2 && (
            <CorrelationMatrix
              tickers={corrData.tickers}
              pairs={corrData.pairs || []}
              maxCorrelation={corrData.max_correlation ?? 0.7}
              anyBreach={corrData.any_breach}
            />
          )}

          {/* Detail table */}
          <PositionTable positions={positions} />
        </>
      )}
    </div>
  );
};

export default RiskDashboard;
