import React, { useState, useEffect, useCallback } from 'react';
import { LoadingSpinner, ErrorMessage, ConfirmDialog } from '../../ui';
import {
  Plus, Edit3, Trash2, X, ChevronDown, ChevronUp,
  AlertTriangle, TrendingUp, TrendingDown, CheckCircle,
  XCircle, Clock, Target, Shield, BookOpen, ArrowUpDown
} from 'lucide-react';
import journalService from '../../../services/journalService';
import { useRouter } from '../../../context/RouterContext';
import '../../../styles/journal.css';

const DIRECTIONS = [
  { value: 'Long', label: 'Long', icon: TrendingUp, color: '#22c55e' },
  { value: 'Short', label: 'Short', icon: TrendingDown, color: '#ef4444' }
];

const ENTRY_TYPES = [
  { value: 'Market', label: 'Market' },
  { value: 'Limit', label: 'Limit' },
  { value: 'Stop', label: 'Stop' }
];

const STATUS_OPTIONS = [
  { value: '', label: 'Tất cả' },
  { value: 'Open', label: 'Đang mở' },
  { value: 'Closed', label: 'Đã đóng' },
  { value: 'Cancelled', label: 'Đã hủy' }
];

const TradeLog = () => {
  const { navigate } = useRouter();

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
        setError(result.error?.message || 'Không thể tải danh sách giao dịch');
      }
    } catch (err) {
      setError('Lỗi kết nối server');
    } finally {
      setLoading(false);
    }
  }, [selectedAccountId, statusFilter, directionFilter, tickerFilter]);

  useEffect(() => { loadAccounts(); }, [loadAccounts]);
  useEffect(() => { loadTrades(); }, [loadTrades]);

  useEffect(() => {
    if (selectedAccountId) {
      const acct = accounts.find(a => a.id === selectedAccountId);
      setSelectedAccount(acct || null);
    }
  }, [selectedAccountId, accounts]);

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
      setFormError(result.error?.detail || result.error?.message || 'Lỗi tạo giao dịch');
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
      setFormError(result.error?.detail || result.error?.message || 'Lỗi đóng lệnh');
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
      setFormError(result.error?.detail || result.error?.message || 'Lỗi điều chỉnh stop');
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
          <h3>Chưa có tài khoản nhật ký</h3>
          <p>Vui lòng tạo tài khoản nhật ký giao dịch trước khi ghi sổ giao dịch.</p>
          <button className="btn-primary" onClick={() => navigate('journal-accounts')} style={{ marginTop: '12px' }}>
            <Plus size={16} /> Tạo tài khoản nhật ký
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
          <h2>Sổ giao dịch</h2>
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
            <Plus size={16} /> Thêm giao dịch
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
            <span>Lệnh đang mở: <strong>{cumulativeRisk.open_trade_count}</strong></span>
          </div>
          <div className="risk-stat">
            <Target size={14} />
            <span>Rủi ro tích lũy: <strong className={
              cumulativeRisk.cumulative_risk_percent > selectedAccount.max_cumulative_risk ? 'text-loss' :
              cumulativeRisk.cumulative_risk_percent > selectedAccount.max_cumulative_risk * 0.7 ? 'text-warning' :
              'text-profit'
            }>
              {cumulativeRisk.cumulative_risk_percent.toFixed(1)}%
            </strong> / {selectedAccount.max_cumulative_risk}%</span>
          </div>
          <div className="risk-stat">
            <span>Vốn: <strong>{journalService.formatCurrency(selectedAccount.current_equity, selectedAccount.currency)}</strong></span>
          </div>
          <div className="risk-stat">
            <span>Tổng giao dịch: <strong>{totalTrades}</strong></span>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="trade-filters">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={directionFilter} onChange={e => setDirectionFilter(e.target.value)}>
          <option value="">Tất cả hướng</option>
          <option value="Long">Long</option>
          <option value="Short">Short</option>
        </select>
        <input
          type="text"
          placeholder="Lọc mã CK..."
          value={tickerFilter}
          onChange={e => setTickerFilter(e.target.value.toUpperCase())}
          className="ticker-filter-input"
        />
      </div>

      {/* Trade Table */}
      {loading ? (
        <LoadingSpinner text="Đang tải giao dịch..." />
      ) : sortedTrades.length === 0 ? (
        <div className="journal-empty">
          <BookOpen size={36} strokeWidth={1} />
          <h3>Chưa có giao dịch</h3>
          <p>Thêm giao dịch đầu tiên để bắt đầu theo dõi.</p>
        </div>
      ) : (
        <div className="trade-table-wrapper">
          <table className="trade-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('trade_number')}># <SortIcon field="trade_number" /></th>
                <th onClick={() => handleSort('entry_date')}>Ngày vào <SortIcon field="entry_date" /></th>
                <th onClick={() => handleSort('market_ticker')}>Mã CK <SortIcon field="market_ticker" /></th>
                <th>Hướng</th>
                <th onClick={() => handleSort('entry_price')}>Giá vào <SortIcon field="entry_price" /></th>
                <th>Stop</th>
                <th>KL</th>
                <th>Rủi ro</th>
                <th>Giá thoát</th>
                <th onClick={() => handleSort('net_pnl')}>P/L <SortIcon field="net_pnl" /></th>
                <th onClick={() => handleSort('r_multiple')}>R <SortIcon field="r_multiple" /></th>
                <th>Trạng thái</th>
                <th>Thao tác</th>
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
                      {trade.direction}
                    </span>
                  </td>
                  <td className="num-cell">{formatNum(trade.entry_price, 2)}</td>
                  <td className="num-cell">
                    {formatNum(trade.revised_stop || trade.initial_stop, 2)}
                    {trade.revised_stop && trade.revised_stop !== trade.initial_stop && (
                      <span className="stop-revised-badge" title={`Ban đầu: ${formatNum(trade.initial_stop, 2)}`}>*</span>
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
                      {trade.status === 'Open' ? 'Mở' : trade.status === 'Closed' ? 'Đóng' : 'Hủy'}
                    </span>
                  </td>
                  <td>
                    <div className="trade-actions">
                      {trade.status === 'Open' && (
                        <>
                          <button
                            className="btn-icon"
                            title="Đóng lệnh"
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
                            title="Điều chỉnh stop"
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
                        title="Chỉnh sửa"
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
                        title="Xóa"
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
            <h3>Thêm giao dịch mới</h3>
            {formError && <div className="form-error"><AlertTriangle size={14} /> {formError}</div>}
            <form onSubmit={handleCreateTrade}>
              <div className="form-row">
                <div className="form-group">
                  <label>Ngày vào lệnh</label>
                  <input
                    type="date"
                    value={tradeForm.entry_date}
                    onChange={e => setTradeForm({ ...tradeForm, entry_date: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Mã chứng khoán</label>
                  <input
                    type="text"
                    value={tradeForm.market_ticker}
                    onChange={e => setTradeForm({ ...tradeForm, market_ticker: e.target.value.toUpperCase() })}
                    placeholder="VD: VNM"
                    required
                    maxLength={20}
                  />
                </div>
                <div className="form-group">
                  <label>Hướng</label>
                  <div className="direction-selector">
                    {DIRECTIONS.map(d => (
                      <button
                        key={d.value}
                        type="button"
                        className={`direction-btn ${tradeForm.direction === d.value ? 'active' : ''}`}
                        style={{ borderColor: tradeForm.direction === d.value ? d.color : 'transparent' }}
                        onClick={() => setTradeForm({ ...tradeForm, direction: d.value })}
                      >
                        <d.icon size={14} /> {d.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Giá vào</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.entry_price}
                    onChange={e => setTradeForm({ ...tradeForm, entry_price: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Loại lệnh</label>
                  <select
                    value={tradeForm.entry_type}
                    onChange={e => setTradeForm({ ...tradeForm, entry_type: e.target.value })}
                  >
                    {ENTRY_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Stop ban đầu</label>
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
                  <label>Khối lượng</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.position_size}
                    onChange={e => setTradeForm({ ...tradeForm, position_size: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Phí GD</label>
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
                  <label>Mục tiêu 1</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.objective_1}
                    onChange={e => setTradeForm({ ...tradeForm, objective_1: e.target.value })}
                    placeholder="Tùy chọn"
                  />
                </div>
                <div className="form-group">
                  <label>Mục tiêu 2</label>
                  <input
                    type="number"
                    step="any"
                    value={tradeForm.objective_2}
                    onChange={e => setTradeForm({ ...tradeForm, objective_2: e.target.value })}
                    placeholder="Tùy chọn"
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Lý do vào lệnh</label>
                <textarea
                  value={tradeForm.entry_reason}
                  onChange={e => setTradeForm({ ...tradeForm, entry_reason: e.target.value })}
                  rows={3}
                  placeholder="Mô tả lý do vào lệnh..."
                />
              </div>

              {/* Risk Preview */}
              {previewRisk() && (
                <div className="risk-preview">
                  <div className="risk-preview-item">
                    <span>Rủi ro lệnh:</span>
                    <strong>{formatNum(previewRisk().riskAmt)} {selectedAccount?.currency}</strong>
                  </div>
                  <div className="risk-preview-item">
                    <span>% vốn:</span>
                    <strong className={previewRisk().riskPct > (selectedAccount?.max_risk_per_trade || 2) ? 'text-loss' : 'text-profit'}>
                      {previewRisk().riskPct.toFixed(2)}%
                    </strong>
                  </div>
                </div>
              )}

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={resetTradeForm}>Hủy</button>
                <button type="submit" className="btn-primary">Tạo giao dịch</button>
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
            <h3>Đóng lệnh #{showCloseForm.trade_number} — {showCloseForm.market_ticker}</h3>
            {formError && <div className="form-error"><AlertTriangle size={14} /> {formError}</div>}
            <form onSubmit={handleCloseTrade}>
              <div className="form-row">
                <div className="form-group">
                  <label>Giá thoát</label>
                  <input
                    type="number"
                    step="any"
                    value={closeForm.exit_price}
                    onChange={e => setCloseForm({ ...closeForm, exit_price: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Ngày thoát</label>
                  <input
                    type="date"
                    value={closeForm.exit_date}
                    onChange={e => setCloseForm({ ...closeForm, exit_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Lý do thoát lệnh</label>
                <textarea
                  value={closeForm.exit_reason}
                  onChange={e => setCloseForm({ ...closeForm, exit_reason: e.target.value })}
                  rows={2}
                  placeholder="VD: Chạm stop, đạt mục tiêu, tín hiệu đảo chiều..."
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowCloseForm(null)}>Hủy</button>
                <button type="submit" className="btn-primary">Đóng lệnh</button>
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
            <h3>Điều chỉnh Stop — #{showStopForm.trade_number} {showStopForm.market_ticker}</h3>
            <p className="modal-hint">
              {showStopForm.direction === 'Long'
                ? 'Long: Stop mới phải >= stop hiện tại (chỉ thắt chặt)'
                : 'Short: Stop mới phải <= stop hiện tại (chỉ thắt chặt)'}
            </p>
            <p className="modal-current">
              Stop hiện tại: <strong>{formatNum(showStopForm.revised_stop || showStopForm.initial_stop, 2)}</strong>
            </p>
            {formError && <div className="form-error"><AlertTriangle size={14} /> {formError}</div>}
            <form onSubmit={handleReviseStop}>
              <div className="form-group">
                <label>Stop mới</label>
                <input
                  type="number"
                  step="any"
                  value={stopForm.new_stop}
                  onChange={e => setStopForm({ ...stopForm, new_stop: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Lý do điều chỉnh</label>
                <textarea
                  value={stopForm.reason}
                  onChange={e => setStopForm({ ...stopForm, reason: e.target.value })}
                  rows={2}
                  placeholder="VD: Giá vượt qua vùng kháng cự..."
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowStopForm(null)}>Hủy</button>
                <button type="submit" className="btn-primary">Cập nhật Stop</button>
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
            <h3>Ghi chú — #{editingTrade.trade_number} {editingTrade.market_ticker}</h3>
            <div className="form-group">
              <label>Lý do thoát lệnh</label>
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
              <label>Bài học rút ra</label>
              <textarea
                value={editForm[editingTrade.id]?.lessons_learned || ''}
                onChange={e => setEditForm(prev => ({
                  ...prev,
                  [editingTrade.id]: { ...prev[editingTrade.id], lessons_learned: e.target.value }
                }))}
                rows={3}
                placeholder="Ghi lại bài học từ giao dịch này..."
              />
            </div>
            <div className="form-actions">
              <button className="btn-secondary" onClick={() => setEditingTrade(null)}>Hủy</button>
              <button className="btn-primary" onClick={() => { handleUpdateTrade(editingTrade.id); setEditingTrade(null); }}>
                Lưu
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <ConfirmDialog
          title="Xóa giao dịch"
          message={`Xóa giao dịch #${confirmDelete.trade_number} (${confirmDelete.market_ticker})?`}
          onConfirm={handleDeleteTrade}
          onCancel={() => setConfirmDelete(null)}
          confirmText="Xóa"
          cancelText="Hủy"
          variant="danger"
        />
      )}
    </div>
  );
};

export default TradeLog;
