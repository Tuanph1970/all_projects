// F-220..F-223 — WatchlistHeatMap: live card grid for all watchlist tickers
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import helperService from '../../../services/helperService';
import httpClient from '../../../services/httpClient';
import { API_ENDPOINTS } from '../../../constants/api';

// ── Constants ────────────────────────────────────────────────────────────────

const REGIME = {
  TREND_UP:   { labelKey: 'decision_helper.common.regime_trend_up',   bg: '#d1fae5', border: '#6ee7b7', text: '#065f46', dot: '#10b981' },
  TREND_DOWN: { labelKey: 'decision_helper.common.regime_trend_down', bg: '#fee2e2', border: '#fca5a5', text: '#991b1b', dot: '#ef4444' },
  RANGE:      { labelKey: 'decision_helper.common.regime_range',      bg: '#fef9c3', border: '#fde68a', text: '#92400e', dot: '#f59e0b' },
  UNDEFINED:  { labelKey: null,                                        bg: '#f3f4f6', border: '#e5e7eb', text: '#6b7280', dot: '#9ca3af' },
};

const ACTION = {
  BUY:        { label: 'BUY',     color: '#065f46', bg: '#d1fae5', ring: '#10b981' },
  SELL_SHORT: { label: 'SHORT',   color: '#92400e', bg: '#fef3c7', ring: '#f59e0b' },
  SELL:       { label: 'SELL',    color: '#991b1b', bg: '#fee2e2', ring: '#ef4444' },
  COVER:      { label: 'COVER',   color: '#1e40af', bg: '#dbeafe', ring: '#3b82f6' },
  REVERSE:    { label: 'REVERSE', color: '#5b21b6', bg: '#ede9fe', ring: '#8b5cf6' },
  HOLD:       { label: 'HOLD',    color: '#374151', bg: '#f3f4f6', ring: '#9ca3af' },
  WAIT:       { label: 'WAIT',    color: '#6b7280', bg: '#f9fafb', ring: '#d1d5db' },
};

const SORT_KEYS = ['confidence', 'ticker', 'action', 'regime'];

const today = () => new Date().toISOString().split('T')[0];

// ── Sub-components ────────────────────────────────────────────────────────────

const ConfidenceBar = ({ value }) => {
  const pct = Math.round((value ?? 0) * 100);
  const color = pct >= 70 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 }}>
      <div style={{ flex: 1, height: 5, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.4s' }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color, minWidth: 30, textAlign: 'right' }}>{pct}%</span>
    </div>
  );
};

const TickerCard = ({ item, onDrillDown }) => {
  const { t } = useTranslation();
  const regime = REGIME[item.regime] || REGIME.UNDEFINED;
  const action = ACTION[item.action] || ACTION.WAIT;
  const actionable = item.is_actionable;

  return (
    <div
      onClick={() => onDrillDown(item.ticker)}
      style={{
        background: regime.bg,
        border: `2px solid ${actionable ? action.ring : regime.border}`,
        borderRadius: 10,
        padding: '14px 16px',
        cursor: 'pointer',
        transition: 'box-shadow 0.15s',
        boxShadow: actionable ? `0 0 0 3px ${action.ring}33` : '0 1px 3px rgba(0,0,0,0.06)',
        minWidth: 0,
        position: 'relative',
      }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = `0 4px 12px rgba(0,0,0,0.12)`}
      onMouseLeave={e => e.currentTarget.style.boxShadow = actionable ? `0 0 0 3px ${action.ring}33` : '0 1px 3px rgba(0,0,0,0.06)'}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontWeight: 800, fontSize: 16, color: regime.text, letterSpacing: '0.02em' }}>
          {item.ticker}
        </span>
        <span style={{
          background: action.bg, color: action.color,
          fontSize: 10, fontWeight: 800, padding: '2px 7px',
          borderRadius: 5, letterSpacing: '0.05em',
        }}>{action.label}</span>
      </div>

      {/* Regime + signal */}
      <div style={{ fontSize: 11, color: regime.text, opacity: 0.8, marginBottom: 2 }}>
        <span style={{ marginRight: 6 }}>
          <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: regime.dot, marginRight: 4, verticalAlign: 'middle' }} />
          {regime.labelKey ? t(regime.labelKey) : '—'}
        </span>
        {item.signal_kind && (
          <span style={{ color: '#6b7280' }}>· {item.signal_kind.replace('_', ' ')}</span>
        )}
      </div>

      {/* Confidence bar */}
      <ConfidenceBar value={item.confidence} />

      {/* Prices — only when actionable */}
      {actionable && item.entry_price && (
        <div style={{ marginTop: 8, fontSize: 11, color: regime.text, opacity: 0.85, display: 'flex', gap: 10 }}>
          <span>E {item.entry_price.toFixed(0)}</span>
          {item.stop_price && <span>· S {item.stop_price.toFixed(0)}</span>}
          {item.target_price && <span>· T {item.target_price.toFixed(0)}</span>}
        </div>
      )}

      {/* Error indicator */}
      {item.error && (
        <div style={{ marginTop: 6, fontSize: 10, color: '#dc2626', opacity: 0.8 }}>⚠ scan error</div>
      )}
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

const WatchlistHeatMap = () => {
  const { t } = useTranslation();
  const [items, setItems] = useState([]);           // ScanResultItem[]
  const [watchlistTickers, setWatchlistTickers] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [loadingWl, setLoadingWl] = useState(false);
  const [error, setError] = useState(null);
  const [lastScan, setLastScan] = useState(null);   // ISO date string
  const [sort, setSort] = useState('confidence');
  const [filterAction, setFilterAction] = useState('All');
  const [barDate, setBarDate] = useState(today());
  const [autoNote, setAutoNote] = useState(null);
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => { isMounted.current = false; };
  }, []);

  // Load watchlist once to show empty-state count
  const loadWatchlist = useCallback(async () => {
    setLoadingWl(true);
    try {
      const res = await helperService.getWatchlist();
      const d = res.data || res;
      setWatchlistTickers((d || []).filter(e => e.active).map(e => e.ticker));
    } catch {
      // non-fatal
    } finally {
      setLoadingWl(false);
    }
  }, []);

  // Run scan — auto-populates the helper watchlist from portfolio holdings if empty
  const runScan = useCallback(async () => {
    setScanning(true);
    setError(null);
    setAutoNote(null);

    const wlRes = await helperService.getWatchlist();
    if (wlRes?.success && (wlRes.data || []).length === 0) {
      const portfolioRes = await httpClient.get(API_ENDPOINTS.PORTFOLIO_DEFAULT);
      const portfolioId = portfolioRes.success ? portfolioRes.data?.id : null;
      const [holdingsRes, watchlistRes] = await Promise.allSettled([
        portfolioId
          ? httpClient.get(API_ENDPOINTS.PORTFOLIO_HOLDINGS(portfolioId))
          : Promise.resolve({ success: true, data: [] }),
        httpClient.get(API_ENDPOINTS.WATCHLIST),
      ]);
      const holdings = holdingsRes.status === 'fulfilled' && holdingsRes.value?.success
        ? (holdingsRes.value.data || []) : [];
      const watchlist = watchlistRes.status === 'fulfilled' && watchlistRes.value?.success
        ? (watchlistRes.value.data || []) : [];

      const seen = new Set();
      const tickers = [...holdings, ...watchlist]
        .map(item => item.symbol)
        .filter(sym => sym && !seen.has(sym) && seen.add(sym));

      if (tickers.length > 0) {
        await Promise.all(tickers.map(ticker => helperService.addWatchlist({ ticker })));
        if (isMounted.current) {
          setWatchlistTickers(tickers);
          setAutoNote(`Auto-added ${tickers.join(', ')} from your portfolio.`);
        }
      }
    }

    const res = await helperService.scan(barDate);
    const d = res?.data || res;
    if (isMounted.current) {
      setItems(d?.results || []);
      setLastScan(d?.bar_date || barDate);
      if (!res?.success && !d?.results) {
        setError(res?.error?.message || 'Scan failed');
      }
      setScanning(false);
    }
  }, [barDate]);

  useEffect(() => { loadWatchlist(); }, [loadWatchlist]);

  // Sort + filter
  const filtered = filterAction === 'All'
    ? items
    : filterAction === 'Actionable'
      ? items.filter(i => i.is_actionable)
      : items.filter(i => i.action === filterAction);

  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'confidence') return (b.confidence ?? 0) - (a.confidence ?? 0);
    if (sort === 'ticker') return a.ticker.localeCompare(b.ticker);
    if (sort === 'action') return (a.action ?? '').localeCompare(b.action ?? '');
    if (sort === 'regime') return (a.regime ?? '').localeCompare(b.regime ?? '');
    return 0;
  });

  const actionable = items.filter(i => i.is_actionable);
  const hasScan = items.length > 0;

  const ACTION_FILTERS = ['All', 'Actionable', 'BUY', 'SELL_SHORT', 'HOLD', 'WAIT'];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>{t('decision_helper.heatmap.title')}</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 13 }}>
            {hasScan
              ? t('decision_helper.heatmap.scanned_summary', { count: items.length, actionable: actionable.length, date: lastScan })
              : t('decision_helper.heatmap.watchlist_hint', { count: watchlistTickers.length })}
          </p>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="date"
            value={barDate}
            onChange={e => setBarDate(e.target.value)}
            style={{ padding: '4px 8px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 12, height: 30 }}
          />
          <button
            onClick={runScan}
            disabled={scanning}
            style={{
              padding: '5px 16px', fontWeight: 700, fontSize: 12,
              background: scanning ? '#e5e7eb' : '#6366f1',
              color: scanning ? '#9ca3af' : '#fff',
              border: 'none', borderRadius: 6, cursor: scanning ? 'not-allowed' : 'pointer',
            }}
          >{scanning ? t('decision_helper.common.scanning') : t('decision_helper.heatmap.scan_now')}</button>
        </div>
      </div>

      {/* Summary chips */}
      {hasScan && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          {['TREND_UP', 'TREND_DOWN', 'RANGE', 'UNDEFINED'].map(r => {
            const count = items.filter(i => i.regime === r).length;
            if (!count) return null;
            const rg = REGIME[r];
            return (
              <span key={r} style={{
                background: rg.bg, border: `1px solid ${rg.border}`, color: rg.text,
                fontSize: 11, fontWeight: 600, padding: '3px 9px', borderRadius: 20,
              }}>
                <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: rg.dot, marginRight: 5, verticalAlign: 'middle' }} />
                {rg.labelKey ? t(rg.labelKey) : r}: {count}
              </span>
            );
          })}
          {actionable.length > 0 && (
            <span style={{ background: '#ede9fe', color: '#5b21b6', fontSize: 11, fontWeight: 700, padding: '3px 9px', borderRadius: 20 }}>
              ⚡ {actionable.length} {t('decision_helper.heatmap.filter_actionable').toLowerCase()}
            </span>
          )}
        </div>
      )}

      {/* Controls row */}
      {hasScan && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
          {/* Action filter */}
          <div style={{ display: 'flex', gap: 4 }}>
            {ACTION_FILTERS.map(f => (
              <button
                key={f}
                onClick={() => setFilterAction(f)}
                style={{
                  padding: '3px 10px', fontSize: 11, fontWeight: filterAction === f ? 700 : 400,
                  border: '1px solid', borderColor: filterAction === f ? '#6366f1' : '#e5e7eb',
                  background: filterAction === f ? '#eef2ff' : '#fff',
                  color: filterAction === f ? '#4338ca' : '#374151',
                  borderRadius: 5, cursor: 'pointer',
                }}
              >{f === 'All' ? t('decision_helper.heatmap.filter_all') : f === 'Actionable' ? t('decision_helper.heatmap.filter_actionable') : f}</button>
            ))}
          </div>

          <div style={{ flex: 1 }} />

          {/* Sort */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#6b7280' }}>
            {t('decision_helper.heatmap.sort_label')}
            {SORT_KEYS.map(sk => {
              const sortLabel = t(`decision_helper.heatmap.sort_${sk}`);
              return (
                <button
                  key={sk}
                  onClick={() => setSort(sk)}
                  style={{
                    padding: '3px 9px', fontSize: 11,
                    border: '1px solid', borderColor: sort === sk ? '#6366f1' : '#e5e7eb',
                    background: sort === sk ? '#eef2ff' : '#fff',
                    color: sort === sk ? '#4338ca' : '#374151',
                    fontWeight: sort === sk ? 700 : 400,
                    borderRadius: 5, cursor: 'pointer',
                  }}
                >{sortLabel}</button>
              );
            })}
          </div>
        </div>
      )}

      {/* Auto-populate note */}
      {autoNote && (
        <div style={{ padding: '10px 14px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, color: '#1d4ed8', marginBottom: 14, fontSize: 13, display: 'flex', gap: 8, alignItems: 'center' }}>
          ℹ️ {autoNote}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ padding: 14, background: '#fee2e2', borderRadius: 8, color: '#991b1b', marginBottom: 16, fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* Empty state */}
      {!hasScan && !scanning && !error && (
        <div style={{ padding: 60, textAlign: 'center', color: '#9ca3af' }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>📊</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#6b7280', marginBottom: 6 }}>{t('decision_helper.heatmap.no_results_title')}</div>
          <div style={{ fontSize: 12 }}>
            {watchlistTickers.length > 0
              ? t('decision_helper.heatmap.no_results_with_tickers', { count: watchlistTickers.length })
              : t('decision_helper.heatmap.no_results_empty')}
          </div>
        </div>
      )}

      {scanning && !hasScan && (
        <div style={{ padding: 60, textAlign: 'center', color: '#6b7280' }}>
          <div style={{ fontSize: 14 }}>{t('decision_helper.heatmap.scanning_progress', { count: watchlistTickers.length })}</div>
        </div>
      )}

      {/* Card grid */}
      {sorted.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: 12,
        }}>
          {sorted.map(item => (
            <TickerCard
              key={item.ticker}
              item={item}
              onDrillDown={(ticker) => {
                window.location.href = `/decision-console?ticker=${ticker}`;
              }}
            />
          ))}
        </div>
      )}

      {hasScan && sorted.length === 0 && (
        <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
          {t('decision_helper.heatmap.no_filter_match')}
        </div>
      )}
    </div>
  );
};

export default WatchlistHeatMap;
