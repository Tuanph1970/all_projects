// F-032 — WatchlistDecisionBoard
// Multi-symbol table: regime, signal, action, confidence, stop, target.
// Fetches watchlist from portfolio-service, then runs /recommend for each.
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RefreshCw, TrendingUp, TrendingDown, Minus, Zap,
  BookOpen, ChevronUp, ChevronDown as ChevDown,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import httpClient from '../../../services/httpClient';
import helperService from '../../../services/helperService';
import { API_ENDPOINTS } from '../../../constants/api';
import TradePlanModal from '../../common/TradePlanModal';

const today = () => new Date().toISOString().split('T')[0];

const REGIME_META = {
  TREND_UP:   { labelKey: 'decision_helper.common.regime_trend_up',   color: '#10b981', Icon: TrendingUp },
  TREND_DOWN: { labelKey: 'decision_helper.common.regime_trend_down', color: '#ef4444', Icon: TrendingDown },
  RANGE:      { labelKey: 'decision_helper.common.regime_range',      color: '#f59e0b', Icon: Minus },
  UNDEFINED:  { labelKey: null,                                        color: '#6b7280', Icon: Minus },
};

const ACTION_META = {
  BUY:        { color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  SELL:       { color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  SELL_SHORT: { color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  COVER:      { color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  HOLD:       { color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)' },
  WAIT:       { color: '#6b7280', bg: 'rgba(107,114,128,0.15)' },
  REVERSE:    { color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)' },
};

const fmt = (v) => v != null
  ? Number(v).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  : '—';

const WatchlistDecisionBoard = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [barDate, setBarDate] = useState(today());
  const [rows, setRows] = useState([]);        // { ticker, status, rec }
  const [analyzing, setAnalyzing] = useState(false);
  const [sortKey, setSortKey] = useState('ticker');
  const [sortAsc, setSortAsc] = useState(true);
  const [planRec, setPlanRec] = useState(null);

  // Load watchlist tickers from portfolio-service
  useEffect(() => {
    httpClient.get(API_ENDPOINTS.WATCHLIST)
      .then(data => {
        const list = Array.isArray(data) ? data : (data.watchlist || data.items || []);
        setRows(list.map(item => ({
          ticker: item.symbol || item.ticker || item,
          status: 'idle',
          rec: null,
        })));
      })
      .catch(() => {
        // fallback: a few common VN tickers
        setRows(['VIC', 'VNM', 'VCB', 'FPT', 'HPG'].map(t => ({ ticker: t, status: 'idle', rec: null })));
      });
  }, []);

  const analyzeOne = useCallback(async (ticker) => {
    setRows(prev => prev.map(r => r.ticker === ticker ? { ...r, status: 'loading' } : r));
    try {
      const rec = await helperService.recommend({ ticker, barDate });
      setRows(prev => prev.map(r => r.ticker === ticker ? { ...r, status: 'done', rec } : r));
    } catch {
      setRows(prev => prev.map(r => r.ticker === ticker ? { ...r, status: 'error', rec: null } : r));
    }
  }, [barDate]);

  const analyzeAll = useCallback(async () => {
    setAnalyzing(true);
    await Promise.all(rows.map(r => analyzeOne(r.ticker)));
    setAnalyzing(false);
  }, [rows, analyzeOne]);

  const handleSort = (key) => {
    if (sortKey === key) setSortAsc(a => !a);
    else { setSortKey(key); setSortAsc(true); }
  };

  const sorted = [...rows].sort((a, b) => {
    const av = sortKey === 'ticker' ? a.ticker
      : sortKey === 'action' ? (a.rec?.action || '')
      : sortKey === 'regime' ? (a.rec?.regime || '')
      : sortKey === 'confidence' ? (a.rec?.confidence || 0)
      : a.ticker;
    const bv = sortKey === 'ticker' ? b.ticker
      : sortKey === 'action' ? (b.rec?.action || '')
      : sortKey === 'regime' ? (b.rec?.regime || '')
      : sortKey === 'confidence' ? (b.rec?.confidence || 0)
      : b.ticker;
    return sortAsc
      ? (typeof av === 'string' ? av.localeCompare(bv) : av - bv)
      : (typeof av === 'string' ? bv.localeCompare(av) : bv - av);
  });

  const SortIcon = ({ k }) => sortKey === k
    ? (sortAsc ? <ChevronUp size={12} /> : <ChevDown size={12} />)
    : null;

  const analyzed = rows.filter(r => r.status === 'done').length;

  return (
    <div style={styles.page}>
      {/* toolbar */}
      <div style={styles.toolbar}>
        <h2 style={styles.title}>{t('decision_helper.decision_board.title')}</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            type="date" value={barDate}
            onChange={e => setBarDate(e.target.value)}
            style={styles.dateInput}
          />
          <button onClick={analyzeAll} disabled={analyzing || rows.length === 0} style={styles.analyzeAllBtn}>
            {analyzing
              ? <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />
              : <Zap size={14} />}
            {t('decision_helper.decision_board.analyze_all', { count: rows.length })}
          </button>
        </div>
      </div>

      {analyzed > 0 && (
        <div style={styles.summary}>
          {['BUY','SELL_SHORT','HOLD','WAIT','REVERSE','SELL','COVER'].map(action => {
            const count = rows.filter(r => r.rec?.action === action).length;
            if (!count) return null;
            const meta = ACTION_META[action] || {};
            return (
              <span key={action} style={{ ...styles.summaryTag, background: meta.bg, color: meta.color }}>
                {action} {count}
              </span>
            );
          })}
        </div>
      )}

      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              {[
                ['ticker', t('decision_helper.decision_board.ticker')],
                ['regime', t('decision_helper.decision_board.regime')],
                ['action', t('decision_helper.decision_board.action')],
                ['confidence', t('decision_helper.decision_board.confidence_short')],
              ].map(([k, label]) => (
                <th key={k} onClick={() => handleSort(k)} style={styles.th}>
                  {label} <SortIcon k={k} />
                </th>
              ))}
              <th style={styles.th}>{t('decision_helper.decision_board.entry')}</th>
              <th style={styles.th}>{t('decision_helper.decision_board.stop')}</th>
              <th style={styles.th}>{t('decision_helper.decision_board.target')}</th>
              <th style={styles.th}>{t('decision_helper.decision_board.shares')}</th>
              <th style={styles.th}></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(({ ticker, status, rec }) => {
              const regime = rec ? REGIME_META[rec.regime] || REGIME_META.UNDEFINED : null;
              const action = rec ? ACTION_META[rec.action] || ACTION_META.WAIT : null;
              const isEntry = rec && ['BUY', 'SELL_SHORT'].includes(rec.action);
              return (
                <tr key={ticker} style={styles.tr}>
                  <td style={styles.td}>
                    <button
                      onClick={() => navigate(`/decision-console?ticker=${ticker}`)}
                      style={styles.tickerLink}
                    >
                      {ticker}
                    </button>
                  </td>
                  <td style={styles.td}>
                    {regime
                      ? <span style={{ color: regime.color, fontSize: 12, fontWeight: 600 }}>{regime.labelKey ? t(regime.labelKey) : '—'}</span>
                      : <span style={{ color: '#6b7280' }}>—</span>}
                  </td>
                  <td style={styles.td}>
                    {action
                      ? <span style={{ ...styles.actionTag, background: action.bg, color: action.color }}>
                          {rec.action}
                        </span>
                      : <span style={{ color: '#6b7280' }}>—</span>}
                  </td>
                  <td style={styles.td}>
                    {rec ? `${(rec.confidence * 100).toFixed(0)}%` : '—'}
                  </td>
                  <td style={styles.td}>{fmt(rec?.entry_price)}</td>
                  <td style={{ ...styles.td, color: '#ef4444' }}>{fmt(rec?.stop_price)}</td>
                  <td style={{ ...styles.td, color: '#10b981' }}>{fmt(rec?.target_price)}</td>
                  <td style={styles.td}>{rec?.position_size ?? '—'}</td>
                  <td style={styles.td}>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button
                        onClick={() => analyzeOne(ticker)}
                        disabled={status === 'loading'}
                        style={styles.iconBtn}
                        title={t('decision_helper.decision_board.recompute')}
                      >
                        <RefreshCw size={12} style={status === 'loading' ? { animation: 'spin 1s linear infinite' } : {}} />
                      </button>
                      {isEntry && (
                        <button
                          onClick={() => setPlanRec(rec)}
                          style={{ ...styles.iconBtn, color: '#3b82f6' }}
                          title={t('decision_helper.decision_board.save_plan')}
                        >
                          <BookOpen size={12} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <TradePlanModal
        isOpen={!!planRec}
        onClose={() => setPlanRec(null)}
        recommendation={planRec}
        onSaved={() => { setPlanRec(null); alert(t('decision_helper.decision_board.plan_saved')); }}
      />

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

const styles = {
  page: { padding: 20, color: '#f9fafb' },
  toolbar: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: 14,
  },
  title: { fontSize: 20, fontWeight: 800, margin: 0 },
  dateInput: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 7,
    padding: '7px 10px', color: '#f9fafb', fontSize: 13, outline: 'none',
  },
  analyzeAllBtn: {
    background: '#3b82f6', border: 'none', borderRadius: 7,
    padding: '8px 16px', color: '#fff', fontWeight: 600, fontSize: 13,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
  },
  summary: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 },
  summaryTag: {
    padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600,
  },
  tableWrap: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: {
    background: '#1f2937', padding: '10px 12px', textAlign: 'left',
    color: '#9ca3af', fontWeight: 600, fontSize: 11, textTransform: 'uppercase',
    letterSpacing: 0.5, cursor: 'pointer', userSelect: 'none',
    borderBottom: '1px solid #374151',
  },
  tr: { borderBottom: '1px solid #1f2937', ':hover': { background: '#1f2937' } },
  td: { padding: '10px 12px', color: '#d1d5db', verticalAlign: 'middle' },
  tickerLink: {
    background: 'none', border: 'none', color: '#60a5fa',
    fontWeight: 700, fontSize: 14, cursor: 'pointer', padding: 0,
  },
  actionTag: {
    padding: '2px 8px', borderRadius: 5, fontWeight: 700, fontSize: 11,
    letterSpacing: 0.5,
  },
  iconBtn: {
    background: '#374151', border: 'none', borderRadius: 5,
    padding: '4px 6px', color: '#9ca3af', cursor: 'pointer',
    display: 'flex', alignItems: 'center',
  },
};

export default WatchlistDecisionBoard;
