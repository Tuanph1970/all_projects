import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { LoadingSpinner, ErrorMessage, ConfirmDialog } from '../../ui';
import {
  Plus, Edit3, Trash2, X, ChevronDown, ChevronUp,
  AlertTriangle, TrendingUp, TrendingDown, CheckCircle,
  XCircle, Clock, Target, Shield, BookOpen, ArrowUpDown,
  CalendarDays, Lightbulb
} from 'lucide-react';
import journalService from '../../../services/journalService';
import httpClient from '../../../services/httpClient';
import { API_ENDPOINTS } from '../../../constants/api';
import { useNavigate } from 'react-router-dom';
import '../../../styles/journal.css';

const DIRECTIONS = [
  { value: 'Long', labelKey: 'journal.trade_log.direction_long', icon: TrendingUp, color: '#22c55e' },
  { value: 'Short', labelKey: 'journal.trade_log.direction_short', icon: TrendingDown, color: '#ef4444' }
];

const ENTRY_TYPES = [
  { value: 'Market', labelKey: 'journal.trade_log.entry_type_market' },
  { value: 'Limit', labelKey: 'journal.trade_log.entry_type_limit' },
  { value: 'Stop', labelKey: 'journal.trade_log.entry_type_stop' }
];

const STATUS_OPTIONS = [
  { value: '', labelKey: 'journal.common.all_option' },
  { value: 'Open', labelKey: 'journal.trade_log.open_status' },
  { value: 'Closed', labelKey: 'journal.trade_log.closed_status' },
  { value: 'Cancelled', labelKey: 'journal.trade_log.cancelled_status' }
];

const TradeLog = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // Account selection
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [selectedAccount, setSelectedAccount] = useState(null);

  // Trade data
  const [trades, setTrades] = useState([]);
  const [totalTrades, setTotalTrades] = useState(0);
  const [cumulativeRisk, setCumulativeRisk] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Today's plan (Journal polish B — surface DailyPlan in TradeLog)
  const [todayPlan, setTodayPlan] = useState(null);
  const [todayPlanCollapsed, setTodayPlanCollapsed] = useState(false);

  // Bought stocks (portfolio holdings, excluding watchlist-only) — the Journal
  // only logs trades on symbols the user actually owns.
  const [boughtSymbols, setBoughtSymbols] = useState([]);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [directionFilter, setDirectionFilter] = useState('');
  const [tickerFilter, setTickerFilter] = useState('');

  // Sorting
  const [sortField, setSortField] = useState('trade_number');
  const [sortDir, setSortDir] = useState('desc');

  // Forms
  const [showTradeForm, setShowTradeForm] = useState(false);
  const [editingTrade, setEditingTrade] = useState(null);
  const [showCloseForm, setShowCloseForm] = useState(null);
  const [showStopForm, setShowStopForm] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [formError, setFormError] = useState(null);
  const [warnings, setWarnings] = useState([]);

  // Trade form
  const [tradeForm, setTradeForm] = useState({
    entry_date: new Date().toISOString().split('T')[0],
    market_ticker: '',
    direction: 'Long',
    entry_price: '',
    entry_type: 'Market',
    initial_stop: '',
    position_size: '',
    commission: '0',
    objective_1: '',
    objective_2: '',
    entry_reason: ''
  });

  // Close form
  const [closeForm, setCloseForm] = useState({
    exit_price: '',
    exit_date: new Date().toISOString().split('T')[0],
    exit_reason: ''
  });

  // Stop revision form
  const [stopForm, setStopForm] = useState({
    new_stop: '',
    reason: ''
  });

  // Edit form for lessons/exit info
  const [editForm, setEditForm] = useState({});

  // =========================================================================
  // Load Data
  // =========================================================================

  const loadAccounts = useCallback(async () => {
    const result = await journalService.getAccounts();
    if (result.success) {
      setAccounts(result.data);
      if (result.data.length > 0 && !selectedAccountId) {
        setSelectedAccountId(result.data[0].id);
        setSelectedAccount(result.data[0]);
      }
    }
  }, [selectedAccountId]);

  const loadTrades = useCallback(async () => {
    if (!selectedAccountId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await journalService.getTrades(selectedAccountId, {
        status: statusFilter || undefined,
        direction: directionFilter || undefined,
        ticker: tickerFilter || undefined,
        limit: 100,
        offset: 0
      });
      if (result.success) {
        setTrades(result.data.trades || []);
        setTotalTrades(result.data.total || 0);
        setCumulativeRisk(result.data.cumulative_risk || null);
      } else {
        setError(result.error?.message || t('journal.trade_log.error_loading_trades'));
      }
    } catch (err) {
      setError(t('journal.common.connection_error'));
    } finally {
      setLoading(false);
    }
  }, [selectedAccountId, statusFilter, directionFilter, tickerFilter, t]);

  useEffect(() => { loadAccounts(); }, [loadAccounts]);
  useEffect(() => { loadTrades(); }, [loadTrades]);

  useEffect(() => {
    if (selectedAccountId) {
      const acct = accounts.find(a => a.id === selectedAccountId);
      setSelectedAccount(acct || null);
    }
  }, [selectedAccountId, accounts]);

  // Load today's DailyPlan so the trader can see their plan while logging.
  // No by-date endpoint exists; list is ordered plan_date desc so today
  // (if present) is at the top among recent entries.
  useEffect(() => {
    if (!selectedAccountId) {
      setTodayPlan(null);
      return;
    }
    (async () => {
      try {
        const today = new Date().toISOString().split('T')[0];
        const res = await journalService.getDailyPlans(selectedAccountId, 30, 0);
        const data = res.data || res || [];
        const list = Array.isArray(data) ? data : (data.items || []);
        setTodayPlan(list.find((p) => p.plan_date === today) || null);
      } catch {
        setTodayPlan(null);
      }
    })();
  }, [selectedAccountId]);

  // Load the user's bought stocks from their default portfolio (holdings where
  // is_watchlist_only is false). Used to constrain the new-trade symbol picker.
  useEffect(() => {
    (async () => {
      try {
        const pr = await httpClient.get(API_ENDPOINTS.PORTFOLIO_DEFAULT);
        const pid = pr.success ? pr.data?.id : null;
        if (!pid) { setBoughtSymbols([]); return; }
        const hr = await httpClient.get(API_ENDPOINTS.PORTFOLIO_HOLDINGS(pid));
        const list = hr.success ? (hr.data || []) : [];
        const symbols = [...new Set(
          list.filter(h => !h.is_watchlist_only && h.symbol).map(h => h.symbol)
        )].sort();
        setBoughtSymbols(symbols);
      } catch {
        setBoughtSymbols([]);
      }
    })();
  }, []);

  // =========================================================================
  // Sorting
  // =========================================================================

  const sortedTrades = [...trades].sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];
    if (aVal == null) return 1;
    if (bVal == null) return -1;
    if (typeof aVal === 'string') aVal = aVal.toLowerCase();
    if (typeof bVal === 'string') bVal = bVal.toLowerCase();
    if (sortDir === 'asc') return aVal > bVal ? 1 : -1;
    return aVal < bVal ? 1 : -1;
  });

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <ArrowUpDown size={12} className="sort-icon-inactive" />;
    return sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
  };

  // =========================================================================
  // Form Handlers
  // =========================================================================

  const resetTradeForm = () => {
    setTradeForm({
      entry_date: new Date().toISOString().split('T')[0],
      market_ticker: '',
      direction: 'Long',
      entry_price: '',
      entry_type: 'Market',
      initial_stop: '',
      position_size: '',
      commission: '0',
      objective_1: '',
      objective_2: '',
      entry_reason: ''
    });
    setEditingTrade(null);
    setShowTradeForm(false);
    setFormError(null);
    setWarnings([]);
  };

  const handleCreateTrade = async (e) => {
    e.preventDefault();
    setFormError(null);

    const payload = {
      entry_date: tradeForm.entry_date,
      market_ticker: tradeForm.market_ticker.toUpperCase(),
      direction: tradeForm.direction,
      entry_price: parseFloat(tradeForm.entry_price),
      entry_type: tradeForm.entry_type,
      initial_stop: parseFloat(tradeForm.initial_stop),
      position_size: parseFloat(tradeForm.position_size),
      commission: parseFloat(tradeForm.commission) || 0,
      ...(tradeForm.objective_1 ? { objective_1: parseFloat(tradeForm.objective_1) } : {}),
      ...(tradeForm.objective_2 ? { objective_2: parseFloat(tradeForm.objective_2) } : {}),
      ...(tradeForm.entry_reason ? { entry_reason: tradeForm.entry_reason } : {})
    };

    const result = await journalService.createTrade(selectedAccountId, payload);
    if (result.success) {
      if (result.data.warnings && result.data.warnings.length > 0) {
        setWarnings(result.data.warnings);
      }
      resetTradeForm();
      loadTrades();
    } else {
      setFormError(result.error?.detail || result.error?.message || t('journal.trade_log.error_creating_trade'));
    }
  };

  const handleUpdateTrade = async (tradeId) => {
    const data = editForm[tradeId];
    if (!data) return;

    const result = await journalService.updateTrade(selectedAccountId, tradeId, data);
    if (result.success) {
      setEditForm(prev => {
        const next = { ...prev };
        delete next[tradeId];
        return next;
      });
      loadTrades();
    }
  };

  const handleCloseTrade = async (e) => {
    e.preventDefault();
    if (!showCloseForm) return;

    const result = await journalService.closeTrade(
      selectedAccountId,
      showCloseForm.id,
      parseFloat(closeForm.exit_price),
      closeForm.exit_date,
      closeForm.exit_reason || undefined
    );

    if (result.success) {
      setShowCloseForm(null);
      setCloseForm({ exit_price: '', exit_date: new Date().toISOString().split('T')[0], exit_reason: '' });
      loadTrades();
    } else {
      setFormError(result.error?.detail || result.error?.message || t('journal.trade_log.error_closing_trade'));
    }
  };

  const handleReviseStop = async (e) => {
    e.preventDefault();
    if (!showStopForm) return;

    const result = await journalService.reviseStop(selectedAccountId, showStopForm.id, {
      new_stop: parseFloat(stopForm.new_stop),
      reason: stopForm.reason || undefined
    });

    if (result.success) {
      setShowStopForm(null);
      setStopForm({ new_stop: '', reason: '' });
      loadTrades();
    } else {
      setFormError(result.error?.detail || result.error?.message || t('journal.trade_log.error_revising_stop'));
    }
  };

  const handleDeleteTrade = async () => {
    if (!confirmDelete) return;
    const result = await journalService.deleteTrade(selectedAccountId, confirmDelete.id);
    if (result.success) {
      setConfirmDelete(null);
      loadTrades();
    }
  };

  // =========================================================================
  // Computed risk for new trade preview
  // =========================================================================

  const previewRisk = () => {
    const entry = parseFloat(tradeForm.entry_price);
    const stop = parseFloat(tradeForm.initial_stop);
    const size = parseFloat(tradeForm.position_size);
    if (!entry || !stop || !size || !selectedAccount) return null;

    const riskAmt = Math.abs(entry - stop) * size;
    const riskPct = selectedAccount.current_equity > 0
      ? (riskAmt / selectedAccount.current_equity) * 100
      : 0;

    return { riskAmt, riskPct };
  };

  // =========================================================================
  // Render Helpers
  // =========================================================================

  const formatNum = (val, decimals = 0) => {
    if (val == null) return '—';
    return val.toLocaleString('vi-VN', { maximumFractionDigits: decimals });
  };

  const pnlClass = (val) => {
    if (val == null) return '';
    return val > 0 ? 'text-profit' : val < 0 ? 'text-loss' : '';
  };

  const rMultipleClass = (val) => {
    if (val == null) return '';
    return val >= 1 ? 'text-profit' : val < 0 ? 'text-loss' : 'text-warning';
  };

  if (accounts.length === 0 && !loading) {
    return (
      <div className="journal-accounts">
        <div className="journal-empty">
          <BookOpen size={48} strokeWidth={1} />
          <h3>{t('journal.common.no_accounts_title')}</h3>
          <p>{t('journal.trade_log.create_account_first_hint')}</p>
          <button className="btn-primary" onClick={() => navigate('/journal-accounts')} style={{ marginTop: '12px' }}>
            <Plus size={16} /> {t('journal.common.create_account_btn')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="trade-log">
      {/* Header */}
      <div className="journal-header">
        <div className="journal-title">
          <BookOpen size={24} />
          <h2>{t('journal.trade_log.title')}</h2>
        </div>
        <div className="trade-log-actions">
          {/* Account Selector */}
          <select
            className="account-selector"
            value={selectedAccountId || ''}
            onChange={e => setSelectedAccountId(parseInt(e.target.value))}
          >
            {accounts.map(a => (
              <option key={a.id} value={a.id}>{a.account_name}</option>
            ))}
          </select>
          <button className="btn-primary" onClick={() => setShowTradeForm(true)}>
            <Plus size={16} /> {t('journal.trade_log.add_trade_btn')}
          </button>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadTrades} />}

      {/* Risk Warnings */}
      {warnings.length > 0 && (
        <div className="risk-warnings">
          {warnings.map((w, i) => (
            <div key={i} className={`risk-warning risk-${w.level}`}>
              <AlertTriangle size={16} />
              <span>{w.message}</span>
              <button className="btn-icon" onClick={() => setWarnings(prev => prev.filter((_, idx) => idx !== i))}>
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Risk Summary Bar */}
      {cumulativeRisk && selectedAccount && (
        <div className="risk-summary-bar">
          <div className="risk-stat">
            <Shield size={14} />
            <span>{t('journal.trade_log.open_trades_label')}<strong>{cumulativeRisk.open_trade_count}</strong></span>
          </div>
          <div className="risk-stat">
            <Target size={14} />
            <span>{t('journal.trade_log.cumulative_risk_label')}<strong className={
              cumulativeRisk.cumulative_risk_percent > selectedAccount.max_cumulative_risk ? 'text-loss' :
              cumulativeRisk.cumulative_risk_percent > selectedAccount.max_cumulative_risk * 0.7 ? 'text-warning' :
              'text-profit'
            }>
              {cumulativeRisk.cumulative_risk_percent.toFixed(1)}%
            </strong> / {selectedAccount.max_cumulative_risk}%</span>
          </div>
          <div className="risk-stat">
            <span>{t('journal.trade_log.equity_label')}<strong>{journalService.formatCurrency(selectedAccount.current_equity, selectedAccount.currency)}</strong></span>
          </div>
          <div className="risk-stat">
            <span>{t('journal.trade_log.total_trades_label')}<strong>{totalTrades}</strong></span>
          </div>
        </div>
      )}

      {/* Today's plan reminder (read-only, from /accounts/{id}/plans). */}
      {todayPlan ? (
        <div className="tlog-today-plan" data-testid="today-plan">
          <div
            className="tlog-today-plan-header"
            onClick={() => setTodayPlanCollapsed((v) => !v)}
            role="button"
            tabIndex={0}
          >
            <CalendarDays size={16} />
            <h4>{t('journal.trade_log.today_plan_title')}</h4>
            <span className="tlog-today-plan-spacer" />
            {todayPlanCollapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </div>
          {!todayPlanCollapsed && (
            <div className="tlog-today-plan-body">
              {todayPlan.new_trade_ideas && (
                <div className="tlog-today-plan-section">
                  <div className="tlog-today-plan-label">
                    <Lightbulb size={13} />
                    <span>{t('journal.trade_log.trade_ideas_label')}</span>
                  </div>
                  <p>{todayPlan.new_trade_ideas}</p>
                </div>
              )}
              {todayPlan.market_review && (
                <div className="tlog-today-plan-section">
                  <div className="tlog-today-plan-label">
                    <BookOpen size={13} />
                    <span>{t('journal.trade_log.market_review_label')}</span>
                  </div>
                  <p>{todayPlan.market_review}</p>
                </div>
              )}
              <button
                className="btn-secondary btn-sm tlog-today-plan-link"
                onClick={() => navigate('/daily-planning')}
              >
                {t('journal.trade_log.open_daily_plan_btn')}
              </button>
            </div>
          )}
        </div>
      ) : selectedAccountId ? (
        <div className="tlog-today-plan tlog-today-plan-empty" data-testid="today-plan-empty">
          <CalendarDays size={16} />
          <span>{t('journal.trade_log.no_plan_today')}</span>
          <button className="btn-secondary btn-sm" onClick={() => navigate('/daily-planning')}>
            {t('journal.trade_log.create_plan_btn')}
          </button>
        </div>
      ) : null}

      {/* Filters */}
      <div className="trade-filters">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{t(o.labelKey)}</option>)}
        </select>
        <select value={directionFilter} onChange={e => setDirectionFilter(e.target.value)}>
          <option value="">{t('journal.common.all_option')}</option>
          <option value="Long">{t('journal.trade_log.direction_long')}</option>
          <option value="Short">{t('journal.trade_log.direction_short')}</option>
        </select>
        <input
          type="text"
          placeholder={t('journal.trade_log.ticker_filter_placeholder')}
          value={tickerFilter}
          onChange={e => setTickerFilter(e.target.value.toUpperCase())}
          className="ticker-filter-input"
        />
      </div>

      {/* Trade Table */}
      {loading ? (
        <LoadingSpinner text={t('journal.trade_log.loading_trades')} />
      ) : sortedTrades.length === 0 ? (
        <div className="journal-empty">
          <BookOpen size={36} strokeWidth={1} />
          <h3>{t('journal.trade_log.no_trades_title')}</h3>
          <p>{t('journal.trade_log.no_trades_hint')}</p>
        </div>
      ) : (
        <div className="trade-table-wrapper">
          <table className="trade-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('trade_number')}>{t('journal.trade_log.number_column')} <SortIcon field="trade_number" /></th>
                <th onClick={() => handleSort('entry_date')}>{t('journal.trade_log.entry_date_column')} <SortIcon field="entry_date" /></th>
                <th onClick={() => handleSort('market_ticker')}>{t('journal.common.ticker_column')} <SortIcon field="market_ticker" /></th>
                <th>{t('journal.trade_log.direction_column')}</th>
                <th onClick={() => handleSort('entry_price')}>{t('journal.trade_log.entry_price_column')} <SortIcon field="entry_price" /></th>
                <th>{t('journal.trade_log.stop_column')}</th>
                <th>{t('journal.trade_log.quantity_column')}</th>
                <th>{t('journal.trade_log.risk_column')}</th>
                <th>{t('journal.trade_log.exit_price_column')}</th>
                <th onClick={() => handleSort('net_pnl')}>{t('journal.common.pnl_column')} <SortIcon field="net_pnl" /></th>
                <th onClick={() => handleSort('r_multiple')}>{t('journal.trade_log.r_multiple_column')} <SortIcon field="r_multiple" /></th>
                <th>{t('journal.trade_log.status_column')}</th>
                <th>{t('journal.trade_log.actions_column')}</th>
              </tr>
            </thead>
            <tbody>
              {sortedTrades.map(trade => (
                <tr key={trade.id} className={`trade-row trade-status-${trade.status.toLowerCase()}`}>
                  <td className="trade-number">{trade.trade_number}</td>
                  <td>{trade.entry_date}</td>
                  <td className="ticker-cell"><strong>{trade.market_ticker}</strong></td>
                  <td>
                    <span className={`direction-badge direction-${trade.direction.toLowerCase()}`}>
                      {trade.direction === 'Long' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      {t(trade.direction === 'Long' ? 'journal.trade_log.direction_long' : 'journal.trade_log.direction_short')}
                    </span>
                  </td>
                  <td className="num-cell">{formatNum(trade.entry_price, 2)}</td>
                  <td className="num-cell">
                    {formatNum(trade.revised_stop || trade.initial_stop, 2)}
                    {trade.revised_stop && trade.revised_stop !== trade.initial_stop && (
                      <span className="stop-revised-badge" title={t('journal.trade_log.stop_revised_badge_title', { initial: formatNum(trade.initial_stop, 2) })}>*</span>
                    )}
                  </td>
                  <td className="num-cell">{formatNum(trade.position_size)}</td>
                  <td className="num-cell">
                    <div className="risk-cell">
                      <span>{formatNum(trade.risk_amount)}</span>
                      {trade.risk_percent != null && (
                        <span className={`risk-pct ${trade.risk_percent > (selectedAccount?.max_risk_per_trade || 2) ? 'text-loss' : ''}`}>
                          ({trade.risk_percent.toFixed(1)}%)
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="num-cell">{trade.exit_price ? formatNum(trade.exit_price, 2) : '—'}</td>
                  <td className={`num-cell ${pnlClass(trade.net_pnl)}`}>
                    {trade.net_pnl != null ? formatNum(trade.net_pnl) : '—'}
                  </td>
                  <td className={`num-cell ${rMultipleClass(trade.r_multiple)}`}>
                    {trade.r_multiple != null ? `${trade.r_multiple >= 0 ? '+' : ''}${trade.r_multiple.toFixed(2)}R` : '—'}
                  </td>
                  <td>
                    <span className={`status-badge status-${trade.status.toLowerCase()}`}>
                      {trade.status === 'Open' && <Clock size={12} />}
                      {trade.status === 'Closed' && <CheckCircle size={12} />}
                      {trade.status === 'Cancelled' && <XCircle size={12} />}
                      {trade.status === 'Open' ? t('journal.trade_log.status_open') : trade.status === 'Closed' ? t('journal.trade_log.status_closed') : t('journal.trade_log.status_cancelled')}
                    </span>
                  </td>
                  <td>
                    <div className="trade-actions">
                      {trade.status === 'Open' && (
                        <>
                          <button
                            className="btn-icon"
                            title={t('journal.trade_log.close_trade_btn_title')}
                            onClick={() => {
                              setShowCloseForm(trade);
                              setCloseForm({
                                exit_price: '',
                                exit_date: new Date().toISOString().split('T')[0],
                                exit_reason: ''
                              });
                            }}
                          >
                            <CheckCircle size={14} />
                          </button>
                          <button
                            className="btn-icon"
                            title={t('journal.trade_log.revise_stop_btn_title')}
                            onClick={() => {
                              setShowStopForm(trade);
                              setStopForm({ new_stop: '', reason: '' });
                            }}
                          >
                            <Shield size={14} />
                          </button>
                        </>
                      )}
                      <button
                        className="btn-icon"
                        title={t('journal.trade_log.edit_btn_title')}
                        onClick={() => {
                          setEditingTrade(trade);
                          setEditForm(prev => ({
                            ...prev,
                            [trade.id]: {
                              lessons_learned: trade.lessons_learned || '',
                              exit_reason: trade.exit_reason || ''
                            }
                          }));
                        }}
                      >
                        <Edit3 size={14} />
                      </button>
                      <button
                        className="btn-icon btn-danger"
                        title={t('journal.trade_log.delete_btn_title')}
                        onClick={() => setConfirmDelete(trade)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ================================================================= */}
      {/* New Trade Modal */}
      {/* ================================================================= */}
      {showTradeForm && (
        <div className="journal-modal-overlay" onClick={resetTradeForm}>
          <div className="journal-modal journal-modal-wide" onClick={e => e.stopPropagation()}>
            <h3>{t('journal.trade_log.new_trade_modal_title')}</h3>
            {formError && <div className="form-error"><AlertTriangle size={14} /> {formError}</div>}
            <form onSubmit={handleCreateTrade}>
              <div className="form-row">
                <div className="form-group">
                  <label>{t('journal.trade_log.entry_date_label')}</label>
                  <input
                    type="date"
                    value={tradeForm.entry_date}
                    onChange={e => setTradeForm({ ...tradeForm, entry_date: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>{t('journal.trade_log.ticker_label')}</label>
                  {boughtSymbols.length > 0 ? (
                    <select
                      value={tradeForm.market_ticker}
                      onChange={e => setTradeForm({ ...tradeForm, market_ticker: e.target.value })}
                      required
                    >
                      <option value="">{t('journal.trade_log.ticker_select_placeholder')}</option>
                      {boughtSymbols.map(sym => (
                        <option key={sym} value={sym}>{sym}</option>
                      ))}
                    </select>
                  ) : (
                    <div className="form-hint" style={{ fontSize: 12, color: '#9ca3af' }}>
                      {t('journal.trade_log.ticker_no_holdings')}
                    </div>
                  )}
                </div>
                <div className="form-group">
                  <label>{t('journal.trade_log.direction_label')}</label>
                  <div className="direction-selector">
                    {DIRECTIONS.map(d => (
                      <button
                        key={d.value}
                        type="button"
                        className={`direction-btn ${tradeForm.direction === d.value ? 'active' : ''}`}
                        style={{ borderColor: tradeForm.direction === d.value ? d.color : 'transparent' }}
                        onClick={() => setTradeForm({ ...tradeForm, direction: d.value })}
                      >
                        <d.icon size={14} /> {t(d.labelKey)}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>{t('journal.trade_log.entry_price_label')}</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.entry_price}
                    onChange={e => setTradeForm({ ...tradeForm, entry_price: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>{t('journal.trade_log.entry_type_label')}</label>
                  <select
                    value={tradeForm.entry_type}
                    onChange={e => setTradeForm({ ...tradeForm, entry_type: e.target.value })}
                  >
                    {ENTRY_TYPES.map(et => <option key={et.value} value={et.value}>{t(et.labelKey)}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>{t('journal.trade_log.initial_stop_label')}</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.initial_stop}
                    onChange={e => setTradeForm({ ...tradeForm, initial_stop: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>{t('journal.trade_log.position_size_label')}</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.position_size}
                    onChange={e => setTradeForm({ ...tradeForm, position_size: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>{t('journal.trade_log.commission_label')}</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.commission}
                    onChange={e => setTradeForm({ ...tradeForm, commission: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>{t('journal.trade_log.objective_1_label')}</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.objective_1}
                    onChange={e => setTradeForm({ ...tradeForm, objective_1: e.target.value })}
                    placeholder={t('journal.trade_log.objective_optional')}
                  />
                </div>
                <div className="form-group">
                  <label>{t('journal.trade_log.objective_2_label')}</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.objective_2}
                    onChange={e => setTradeForm({ ...tradeForm, objective_2: e.target.value })}
                    placeholder={t('journal.trade_log.objective_optional')}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>{t('journal.trade_log.entry_reason_label')}</label>
                <textarea
                  value={tradeForm.entry_reason}
                  onChange={e => setTradeForm({ ...tradeForm, entry_reason: e.target.value })}
                  rows={3}
                  placeholder={t('journal.trade_log.entry_reason_placeholder')}
                />
              </div>

              {/* Risk Preview */}
              {previewRisk() && (
                <div className="risk-preview">
                  <div className="risk-preview-item">
                    <span>{t('journal.trade_log.trade_risk_label')}</span>
                    <strong>{formatNum(previewRisk().riskAmt)} {selectedAccount?.currency}</strong>
                  </div>
                  <div className="risk-preview-item">
                    <span>{t('journal.trade_log.percent_equity_label')}</span>
                    <strong className={previewRisk().riskPct > (selectedAccount?.max_risk_per_trade || 2) ? 'text-loss' : 'text-profit'}>
                      {previewRisk().riskPct.toFixed(2)}%
                    </strong>
                  </div>
                </div>
              )}

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={resetTradeForm}>{t('journal.common.cancel_btn')}</button>
                <button type="submit" className="btn-primary">{t('journal.trade_log.create_trade_btn')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* Close Trade Modal */}
      {/* ================================================================= */}
      {showCloseForm && (
        <div className="journal-modal-overlay" onClick={() => setShowCloseForm(null)}>
          <div className="journal-modal" onClick={e => e.stopPropagation()}>
            <h3>{t('journal.trade_log.close_trade_modal_title', { tradeNum: showCloseForm.trade_number, ticker: showCloseForm.market_ticker })}</h3>
            {formError && <div className="form-error"><AlertTriangle size={14} /> {formError}</div>}
            <form onSubmit={handleCloseTrade}>
              <div className="form-row">
                <div className="form-group">
                  <label>{t('journal.trade_log.exit_price_label')}</label>
                  <input
                    type="number"
                    step="any"
                    value={closeForm.exit_price}
                    onChange={e => setCloseForm({ ...closeForm, exit_price: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>{t('journal.trade_log.exit_date_label')}</label>
                  <input
                    type="date"
                    value={closeForm.exit_date}
                    onChange={e => setCloseForm({ ...closeForm, exit_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>{t('journal.trade_log.exit_reason_label')}</label>
                <textarea
                  value={closeForm.exit_reason}
                  onChange={e => setCloseForm({ ...closeForm, exit_reason: e.target.value })}
                  rows={2}
                  placeholder={t('journal.trade_log.exit_reason_placeholder')}
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowCloseForm(null)}>{t('journal.common.cancel_btn')}</button>
                <button type="submit" className="btn-primary">{t('journal.trade_log.close_trade_btn')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* Stop Revision Modal */}
      {/* ================================================================= */}
      {showStopForm && (
        <div className="journal-modal-overlay" onClick={() => setShowStopForm(null)}>
          <div className="journal-modal" onClick={e => e.stopPropagation()}>
            <h3>{t('journal.trade_log.revise_stop_modal_title', { tradeNum: showStopForm.trade_number, ticker: showStopForm.market_ticker })}</h3>
            <p className="modal-hint">
              {showStopForm.direction === 'Long'
                ? t('journal.trade_log.long_stop_hint')
                : t('journal.trade_log.short_stop_hint')}
            </p>
            <p className="modal-current">
              {t('journal.trade_log.current_stop_label')}<strong>{formatNum(showStopForm.revised_stop || showStopForm.initial_stop, 2)}</strong>
            </p>
            {formError && <div className="form-error"><AlertTriangle size={14} /> {formError}</div>}
            <form onSubmit={handleReviseStop}>
              <div className="form-group">
                <label>{t('journal.trade_log.new_stop_label')}</label>
                <input
                  type="number"
                  step="any"
                  value={stopForm.new_stop}
                  onChange={e => setStopForm({ ...stopForm, new_stop: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>{t('journal.trade_log.stop_revision_reason_label')}</label>
                <textarea
                  value={stopForm.reason}
                  onChange={e => setStopForm({ ...stopForm, reason: e.target.value })}
                  rows={2}
                  placeholder={t('journal.trade_log.stop_revision_placeholder')}
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowStopForm(null)}>{t('journal.common.cancel_btn')}</button>
                <button type="submit" className="btn-primary">{t('journal.trade_log.update_stop_btn')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* Edit Trade (Lessons) Modal */}
      {/* ================================================================= */}
      {editingTrade && (
        <div className="journal-modal-overlay" onClick={() => setEditingTrade(null)}>
          <div className="journal-modal" onClick={e => e.stopPropagation()}>
            <h3>{t('journal.trade_log.edit_trade_modal_title', { tradeNum: editingTrade.trade_number, ticker: editingTrade.market_ticker })}</h3>
            <div className="form-group">
              <label>{t('journal.trade_log.exit_reason_label')}</label>
              <textarea
                value={editForm[editingTrade.id]?.exit_reason || ''}
                onChange={e => setEditForm(prev => ({
                  ...prev,
                  [editingTrade.id]: { ...prev[editingTrade.id], exit_reason: e.target.value }
                }))}
                rows={2}
              />
            </div>
            <div className="form-group">
              <label>{t('journal.trade_log.lessons_learned_label')}</label>
              <textarea
                value={editForm[editingTrade.id]?.lessons_learned || ''}
                onChange={e => setEditForm(prev => ({
                  ...prev,
                  [editingTrade.id]: { ...prev[editingTrade.id], lessons_learned: e.target.value }
                }))}
                rows={3}
                placeholder={t('journal.trade_log.lessons_placeholder')}
              />
            </div>
            <div className="form-actions">
              <button className="btn-secondary" onClick={() => setEditingTrade(null)}>{t('journal.common.cancel_btn')}</button>
              <button className="btn-primary" onClick={() => { handleUpdateTrade(editingTrade.id); setEditingTrade(null); }}>
                {t('journal.common.save_btn')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <ConfirmDialog
          title={t('journal.trade_log.delete_trade_confirm_title')}
          message={t('journal.trade_log.delete_trade_confirm_msg', { tradeNum: confirmDelete.trade_number, ticker: confirmDelete.market_ticker })}
          onConfirm={handleDeleteTrade}
          onCancel={() => setConfirmDelete(null)}
          confirmText={t('journal.trade_log.delete_btn')}
          cancelText={t('journal.trade_log.cancel_delete_btn')}
          variant="danger"
        />
      )}
    </div>
  );
};

export default TradeLog;
