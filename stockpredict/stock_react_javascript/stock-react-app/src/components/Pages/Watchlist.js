import React, { useEffect, useState, useCallback } from 'react';
import { Star, Trash2, RefreshCw, Plus, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import httpClient from '../../services/httpClient';
import tcbNewsService from '../../services/tcbNewsService';
import { API_ENDPOINTS } from '../../constants/api';
import { useNavigate } from 'react-router-dom';

// Forward-return horizons, in trading sessions, exactly as the scorer fills them
// (news-service call_scorer.HORIZONS / FR-BM-SCORE).
const HORIZONS = [1, 5, 20, 60];

/** Returns are stored as fractions (0.031 = +3.1%). Null means the horizon has not
 *  elapsed — a dash, never a zero, which would read as "flat". Mirrors TcbNews. */
const pct = (v, digits = 1) =>
  v == null ? '—' : `${v > 0 ? '+' : ''}${(v * 100).toFixed(digits)}%`;

const returnColor = (v) => (v == null ? '#9ca3af' : v < 0 ? '#dc2626' : '#16a34a');

const isoDay = (v) => (typeof v === 'string' ? v.slice(0, 10) : null);

/**
 * The longest horizon that has actually elapsed for one call.
 *
 * The scorer never partially fills a horizon — an unelapsed one stays null rather than
 * borrowing the last available bar — so the largest non-null horizon is the most
 * informative honest answer to "how did this call turn out?", and it is labelled with
 * its horizon so a 1-session number is never mistaken for a 60-session one.
 */
const latestMark = (reco) => {
  if (!reco) return null;
  for (let i = HORIZONS.length - 1; i >= 0; i -= 1) {
    const h = HORIZONS[i];
    const value = reco[`ret_${h}d`];
    if (value != null) {
      return { horizon: h, value, excess: reco[`ret_${h}d_vs_index`] ?? null };
    }
  }
  return null;
};

/**
 * Pick which stored call a watchlist row should report.
 *
 * Prefers the call from the very session the watchlist row cites, so the number always
 * belongs to the proposal on screen. Falling back to the newest call for that symbol
 * keeps a result visible when the two disagree, and the cell then says which session it
 * came from — an unlabelled number from a different call would be worse than none.
 */
const markFor = (ledger, symbol, proposalDate) => {
  const forSymbol = ledger.filter((r) => r.symbol === symbol);
  if (forSymbol.length === 0) return null;
  const wanted = isoDay(proposalDate);
  const exact = wanted && forSymbol.find((r) => isoDay(r.session_date) === wanted);
  if (exact) return { reco: exact, sameSession: true };
  const newest = forSymbol.reduce(
    (a, b) => ((isoDay(a.session_date) || '') >= (isoDay(b.session_date) || '') ? a : b));
  return { reco: newest, sameSession: !wanted };
};

// BUY / SELL / HOLD / WATCH as written to portfolio_holdings.proposal_action.
// WATCH is ours: TCBS's "Chờ mua" is an explicit not-yet-a-buy, so it is not folded
// into BUY. The verbatim wording rides along as the tooltip.
const PROPOSAL_COLORS = {
  BUY: { bg: '#dcfce7', fg: '#166534' },
  SELL: { bg: '#fee2e2', fg: '#991b1b' },
  HOLD: { bg: '#e0e7ff', fg: '#3730a3' },
  WATCH: { bg: '#fef3c7', fg: '#92400e' },
};

const ProposalBadge = ({ action, label }) => {
  const palette = PROPOSAL_COLORS[action] || { bg: '#f3f4f6', fg: '#6b7280' };
  return (
    <span
      title={label || ''}
      style={{
        background: palette.bg, color: palette.fg, borderRadius: 4,
        padding: '2px 8px', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap',
      }}
    >
      {action}
    </span>
  );
};

const Watchlist = () => {
  const { t } = useTranslation();
  const [items, setItems] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [adding, setAdding] = useState(false);

  const navigate = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    // The watchlist is the screen; the TCB ledger only annotates it. Fetched in
    // parallel, and a ledger failure is swallowed deliberately — a news-service outage
    // must cost the operator an extra column, never the watchlist itself.
    const [res, ledgerRes] = await Promise.all([
      httpClient.get(API_ENDPOINTS.WATCHLIST),
      tcbNewsService.recos({ limit: 200 }).catch(() => ({ success: false })),
    ]);
    if (res.success && Array.isArray(res.data)) {
      setItems(res.data);
    } else {
      setError(res.error?.message || t('tools.watchlist.load_error'));
      setItems([]);
    }
    setLedger(ledgerRes?.success && Array.isArray(ledgerRes.data) ? ledgerRes.data : []);
    setLoading(false);
  }, [t]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e) => {
    e.preventDefault();
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol) return;
    setAdding(true);
    setError(null);
    const res = await httpClient.post(API_ENDPOINTS.WATCHLIST, { symbol });
    setAdding(false);
    if (res.success) {
      setNewSymbol('');
      setShowAdd(false);
      load();
    } else {
      setError(res.error?.message || t('tools.watchlist.add_error'));
    }
  };

  const handleRemove = async (symbol) => {
    const res = await httpClient.delete(API_ENDPOINTS.WATCHLIST_REMOVE(symbol));
    if (res.success) {
      setItems(prev => prev.filter(i => (i.symbol || i) !== symbol));
    } else {
      setError(res.error?.message || t('tools.watchlist.remove_error', { symbol }));
    }
  };

  const numLocale = 'vi-VN';
  const formatPrice = (v) => {
    if (v == null) return '—';
    return new Intl.NumberFormat(numLocale).format(v);
  };

  const formatPct = (v) => {
    if (v == null) return '—';
    const sign = v >= 0 ? '+' : '';
    return `${sign}${v.toFixed(2)}%`;
  };

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: 12, margin: 0 }}>
          <Star color="#f59e0b" />
          {t('tools.watchlist.title')}
        </h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={load}
            className="btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            disabled={loading}
            aria-label={t('tools.watchlist.refresh_aria')}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            {t('tools.watchlist.refresh_button')}
          </button>
          <button
            onClick={() => setShowAdd(s => !s)}
            className="btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            {showAdd ? <X size={16} /> : <Plus size={16} />}
            {showAdd ? t('tools.watchlist.cancel_button') : t('tools.watchlist.add_button')}
          </button>
        </div>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <label htmlFor="wl-symbol" className="visually-hidden" style={{ position: 'absolute', left: '-10000px' }}>
            {t('tools.watchlist.stock_code_label')}
          </label>
          <input
            id="wl-symbol"
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            placeholder={t('tools.watchlist.stock_code_placeholder')}
            style={{ flex: 1, padding: 8, border: '1px solid #d1d5db', borderRadius: 6 }}
            autoFocus
            maxLength={10}
            required
          />
          <button type="submit" className="btn-primary" disabled={adding}>
            {adding ? t('tools.watchlist.adding_state') : t('tools.watchlist.save_button')}
          </button>
        </form>
      )}

      {error && (
        <div style={{ padding: 12, background: '#fee2e2', color: '#991b1b', borderRadius: 6, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {loading && items.length === 0 ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#6b7280' }}>{t('tools.watchlist.loading')}</div>
      ) : items.length === 0 ? (
        <div style={{ padding: 48, textAlign: 'center', color: '#6b7280', border: '1px dashed #d1d5db', borderRadius: 8 }}>
          <Star size={48} style={{ margin: '0 auto 12px', color: '#d1d5db' }} />
          <p>{t('tools.watchlist.empty_list')}</p>
          <p style={{ fontSize: 14 }}>{t('tools.watchlist.empty_hint')}</p>
        </div>
      ) : (
        <div style={{ background: '#fff', borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ background: '#f9fafb' }}>
              <tr>
                <th style={{ padding: 12, textAlign: 'left' }}>{t('tools.watchlist.column_symbol')}</th>
                <th style={{ padding: 12, textAlign: 'left' }}>{t('tools.watchlist.column_name')}</th>
                <th style={{ padding: 12, textAlign: 'right' }}>{t('tools.watchlist.column_current_price')}</th>
                <th style={{ padding: 12, textAlign: 'right' }}>{t('tools.watchlist.column_change')}</th>
                <th style={{ padding: 12, textAlign: 'center' }}>{t('tools.watchlist.column_proposal_action')}</th>
                <th style={{ padding: 12, textAlign: 'right' }}>{t('tools.watchlist.column_result')}</th>
                <th style={{ padding: 12, textAlign: 'left' }}>{t('tools.watchlist.column_proposal_by')}</th>
                <th style={{ padding: 12, textAlign: 'center' }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const symbol = item.symbol || item;
                const changePct = item.change_percent ?? item.changePercent;
                const positive = changePct != null && changePct >= 0;
                const matched = markFor(ledger, symbol, item.proposal_date);
                const mark = latestMark(matched?.reco);
                return (
                  <tr key={symbol} style={{ borderTop: '1px solid #f3f4f6' }}>
                    <td style={{ padding: 12 }}>
                      <button
                        onClick={() => navigate(`/company/${symbol}`)}
                        style={{ background: 'none', border: 'none', color: '#2563eb', fontWeight: 600, cursor: 'pointer' }}
                      >
                        {symbol}
                      </button>
                    </td>
                    <td style={{ padding: 12, color: '#4b5563' }}>{item.company_name || item.name || '—'}</td>
                    <td style={{ padding: 12, textAlign: 'right' }}>{formatPrice(item.current_price ?? item.price)}</td>
                    <td style={{ padding: 12, textAlign: 'right', color: positive ? '#16a34a' : '#dc2626' }}>
                      {formatPct(changePct)}
                    </td>
                    <td style={{ padding: 12, textAlign: 'center' }}>
                      {item.proposal_action
                        ? <ProposalBadge action={item.proposal_action} label={item.proposal_label} />
                        : <span style={{ color: '#9ca3af' }}>—</span>}
                    </td>
                    {/* How the call turned out (#57). The ledger lived only on the TCB
                        News screen, so the watch screen showed what TCB said and never
                        whether it worked. */}
                    <td style={{ padding: 12, textAlign: 'right', whiteSpace: 'nowrap' }}>
                      {mark ? (
                        <>
                          <div style={{ color: returnColor(mark.value), fontWeight: 600 }}>
                            {pct(mark.value)}
                            <span style={{ color: '#9ca3af', fontWeight: 400, fontSize: 12 }}>
                              {' '}· {mark.horizon}d
                            </span>
                            {/* An unadjusted mark can be badly wrong: a raw series
                                spanning a bonus issue prices the share-count change as a
                                loss (Backlog #60). Flagged, not hidden. */}
                            {matched.reco.ret_adjusted === false && (
                              <span
                                title={t('tools.watchlist.result_unadjusted')}
                                style={{ color: '#d97706', marginLeft: 4 }}
                              >
                                *
                              </span>
                            )}
                          </div>
                          {/* The benchmark travels with the number (EC-B7), rather than
                              being buried in a tooltip. */}
                          {mark.excess != null && (
                            <div style={{ color: '#6b7280', fontSize: 12 }}>
                              {t('tools.watchlist.result_vs_index', { value: pct(mark.excess) })}
                            </div>
                          )}
                          {!matched.sameSession && (
                            <div
                              style={{ color: '#9ca3af', fontSize: 11 }}
                              title={t('tools.watchlist.result_other_session', {
                                date: isoDay(matched.reco.session_date),
                              })}
                            >
                              {t('tools.watchlist.result_from_session', {
                                date: isoDay(matched.reco.session_date),
                              })}
                            </div>
                          )}
                        </>
                      ) : (
                        <span
                          style={{ color: '#9ca3af' }}
                          title={matched
                            ? t('tools.watchlist.result_not_scored_yet')
                            : t('tools.watchlist.result_no_call')}
                        >
                          —
                        </span>
                      )}
                    </td>
                    <td style={{ padding: 12, color: '#4b5563' }} title={item.proposal_note || ''}>
                      {item.proposal_by || '—'}
                      {item.proposal_date && (
                        <span style={{ color: '#9ca3af', fontSize: 12 }}> · {item.proposal_date}</span>
                      )}
                    </td>
                    <td style={{ padding: 12, textAlign: 'center' }}>
                      <button
                        onClick={() => handleRemove(symbol)}
                        title={t('tools.watchlist.remove_tooltip')}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626' }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Watchlist;
