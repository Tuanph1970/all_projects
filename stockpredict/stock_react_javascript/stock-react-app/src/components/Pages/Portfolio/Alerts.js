import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { LoadingSpinner, ErrorMessage, DataTable, ConfirmDialog } from '../../ui';
import { Bell, BellOff, Plus, Trash2, Edit, TrendingUp, TrendingDown, Calendar } from 'lucide-react';
import { alertsAPI } from '../../../services/api';
import portfolioService from '../../../services/portfolioService';
import { formatVND } from '../../../utils/currencyFormatter';
import '../../../styles/alerts.css';

const Alerts = () => {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingAlert, setEditingAlert] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [userHoldings, setUserHoldings] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('');

  const [formData, setFormData] = useState({
    symbol: '',
    companyName: '',
    alertType: 'price_above',
    targetPrice: '',
    isActive: true,
    notes: ''
  });

  useEffect(() => {
    fetchAlerts();
    loadUserHoldings();
  }, []);

  const loadUserHoldings = async () => {
    try {
      const result = await portfolioService.getPortfolio();
      if (result.success) {
        // Format holdings data for dropdown options
        const formattedHoldings = portfolioService.formatPortfolioData(result.data);
        setUserHoldings(formattedHoldings);
      } else {
        console.error('Failed to load user holdings:', result.error);
        setUserHoldings([]);
      }
    } catch (err) {
      console.error('Failed to load user holdings:', err);
      setUserHoldings([]);
    }
  };

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const alertsData = await alertsAPI.getAlerts();
      setAlerts(alertsData);
    } catch (err) {
      setError(t('portfolio.alerts.fetch_alerts_error'));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const alertData = {
        symbol: formData.symbol,
        companyName: formData.companyName,
        alertType: formData.alertType,
        targetPrice: parseFloat(formData.targetPrice),
        isActive: formData.isActive,
        notes: formData.notes
      };

      if (editingAlert) {
        // Update alert
        await alertsAPI.updateAlert(editingAlert.id, alertData);
      } else {
        // Create new alert
        await alertsAPI.createAlert(alertData);
      }
      
      // Refresh alerts list
      await fetchAlerts();
      resetForm();
    } catch (err) {
      setError(err.message || t('portfolio.alerts.save_alert_error'));
    }
  };

  const handleEdit = (alert) => {
    setEditingAlert(alert);

    // Check if the alert's symbol is in user's current holdings
    const isSymbolInHoldings = userHoldings.some(h => h.symbol === alert.symbol);

    if (isSymbolInHoldings) {
      setSelectedSymbol(alert.symbol);
    } else {
      // Symbol not in current holdings, clear selected symbol to show manual input
      setSelectedSymbol('');
    }

    setFormData({
      symbol: alert.symbol || '',
      companyName: alert.companyName || '',
      alertType: alert.alertType || 'price_above',
      targetPrice: alert.targetPrice != null ? alert.targetPrice.toString() : '',
      isActive: alert.isActive !== false,
      notes: alert.notes || ''
    });
    setShowAddForm(true);
  };

  const handleDelete = async (id) => {
    try {
      await alertsAPI.deleteAlert(id);
      // Refresh alerts list
      await fetchAlerts();
      setConfirmDelete(null);
    } catch (err) {
      setError(err.message || t('portfolio.alerts.delete_alert_error'));
    }
  };

  const toggleAlert = async (id) => {
    try {
      await alertsAPI.toggleAlert(id);
      // Refresh alerts list
      await fetchAlerts();
    } catch (err) {
      setError(err.message || t('portfolio.alerts.toggle_alert_error'));
    }
  };

  const handleStockSelect = (e) => {
    const symbol = e.target.value;
    setSelectedSymbol(symbol);

    if (symbol) {
      const holding = userHoldings.find(h => h.symbol === symbol);
      if (holding) {
        // Use 'name' field from API response (backend returns 'name' not 'company_name')
        setFormData({
          ...formData,
          symbol: holding.symbol,
          companyName: holding.name || holding.company_name || ''
        });
      }
    } else {
      setFormData({
        ...formData,
        symbol: '',
        companyName: ''
      });
    }
  };

  const resetForm = () => {
    setFormData({
      symbol: '',
      companyName: '',
      alertType: 'price_above',
      targetPrice: '',
      isActive: true,
      notes: ''
    });
    setSelectedSymbol('');
    setShowAddForm(false);
    setEditingAlert(null);
  };

  const getAlertStatus = (alert) => {
    if (!alert.isActive) return 'inactive';
    if (alert.triggered) return 'triggered';
    
    const { alertType, targetPrice, currentPrice } = alert;
    if (alertType === 'price_above' && currentPrice >= targetPrice) return 'triggered';
    if (alertType === 'price_below' && currentPrice <= targetPrice) return 'triggered';
    
    return 'active';
  };

  const columns = [
    {
      key: 'symbol',
      header: t('portfolio.alerts.column_symbol'),
      sortable: true,
      render: (value, alert) => (
        <div className="stock-info">
          <span className="symbol">{value}</span>
          <span className="company-name">{alert.companyName}</span>
        </div>
      )
    },
    {
      key: 'alertType',
      header: t('portfolio.alerts.column_alert_type'),
      sortable: true,
      render: (value) => (
        <div className="alert-type" style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 0.875rem',
          borderRadius: '0.5rem',
          fontWeight: 600,
          fontSize: '0.8125rem',
          background: value === 'price_above'
            ? 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)'
            : 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',
          color: value === 'price_above' ? '#15803d' : '#dc2626',
          border: value === 'price_above' ? '1px solid #86efac' : '1px solid #fca5a5'
        }}>
          {value === 'price_above' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
          {value === 'price_above' ? t('portfolio.alerts.price_above_label') : t('portfolio.alerts.price_below_label')}
        </div>
      )
    },
    {
      key: 'targetPrice',
      header: t('portfolio.alerts.column_target_price'),
      sortable: true,
      render: (value) => (
        <span className="price-badge target-price" style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '0.375rem 0.75rem',
          borderRadius: '0.5rem',
          fontWeight: 600,
          fontSize: '0.8125rem',
          fontFamily: "'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace",
          background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
          color: '#92400e',
          border: '1px solid #fcd34d'
        }}>
          {formatVND(typeof value === 'number' ? value : 0)}
        </span>
      )
    },
    {
      key: 'currentPrice',
      header: t('portfolio.alerts.column_current_price'),
      sortable: true,
      render: (value) => (
        <span className="price-badge current-price" style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '0.375rem 0.75rem',
          borderRadius: '0.5rem',
          fontWeight: 600,
          fontSize: '0.8125rem',
          fontFamily: "'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace",
          background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
          color: '#4338ca',
          border: '1px solid #a5b4fc'
        }}>
          {formatVND(typeof value === 'number' ? value : 0)}
        </span>
      )
    },
    {
      key: 'status',
      header: t('portfolio.alerts.column_status'),
      render: (_, alert) => {
        const status = getAlertStatus(alert);
        const statusLabels = {
          'triggered': t('portfolio.alerts.status_triggered'),
          'active': t('portfolio.alerts.status_active'),
          'inactive': t('portfolio.alerts.status_inactive')
        };
        return (
          <span className={`alert-status ${status}`}>
            {status === 'triggered' && <Bell size={14} />}
            {status === 'active' && <Bell size={14} />}
            {status === 'inactive' && <BellOff size={14} />}
            {statusLabels[status] || status}
          </span>
        );
      }
    },
    {
      key: 'createdAt',
      header: t('portfolio.alerts.column_created_at'),
      sortable: true,
      render: (value) => (
        <span className="date-badge" style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.375rem',
          padding: '0.375rem 0.75rem',
          background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
          color: '#0369a1',
          borderRadius: '0.375rem',
          fontSize: '0.8125rem',
          fontWeight: 500,
          border: '1px solid #7dd3fc'
        }}>
          <Calendar size={12} />
          {value || 'N/A'}
        </span>
      )
    },
    {
      key: 'actions',
      header: t('portfolio.alerts.column_actions'),
      render: (_, alert) => (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => toggleAlert(alert.id)}
            className={`action-btn ${alert.isActive ? 'active-btn' : 'inactive-btn'}`}
            title={alert.isActive ? t('portfolio.alerts.deactivate_tooltip') : t('portfolio.alerts.activate_tooltip')}
          >
            {alert.isActive ? <Bell size={18} /> : <BellOff size={18} />}
          </button>
          <button
            onClick={() => handleEdit(alert)}
            className="action-btn edit-btn"
            title={t('portfolio.alerts.edit_tooltip')}
          >
            <Edit size={18} />
          </button>
          <button
            onClick={() => setConfirmDelete(alert)}
            className="action-btn remove-btn"
            title={t('portfolio.alerts.delete_tooltip')}
          >
            <Trash2 size={18} />
          </button>
        </div>
      )
    }
  ];

  if (loading) return <LoadingSpinner />;

  return (
    <div className="alerts-page">
      <div className="page-header">
        <h1>{t('portfolio.alerts.page_title')}</h1>
        <button
          onClick={() => setShowAddForm(true)}
          className="btn btn-primary"
        >
          <Plus size={16} />
          {t('portfolio.alerts.create_alert_button')}
        </button>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <div className="alerts-summary">
        <div className="summary-stats">
          <div className="stat-item">
            <span className="stat-value">{alerts.filter(a => a.isActive).length}</span>
            <span className="stat-label">{t('portfolio.alerts.active_alerts_label')}</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{alerts.filter(a => getAlertStatus(a) === 'triggered').length}</span>
            <span className="stat-label">{t('portfolio.alerts.triggered_alerts_label')}</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{alerts.length}</span>
            <span className="stat-label">{t('portfolio.alerts.total_alerts_label')}</span>
          </div>
        </div>
      </div>

      <div className="alerts-table">
        <DataTable
          data={alerts}
          columns={columns}
          emptyMessage={t('portfolio.alerts.no_alerts_message')}
        />
      </div>

      {showAddForm && (
        <div className="modal-overlay" onClick={resetForm} style={{ display: 'flex', position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.5)', zIndex: 999999, alignItems: 'center', justifyContent: 'center' }}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ display: 'block', backgroundColor: 'white', padding: '2rem', borderRadius: '0.5rem', minWidth: '500px', maxWidth: '600px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)', position: 'relative' }}>
            <div className="modal-header">
              <h2>{editingAlert ? t('portfolio.alerts.edit_alert_modal_title') : t('portfolio.alerts.create_alert_modal_title')}</h2>
              <button onClick={resetForm} className="modal-close">×</button>
            </div>
            <form onSubmit={handleSubmit} className="alert-form">
              <div className="form-group">
                <label>{t('portfolio.alerts.select_stock_label')}</label>
                <select
                  value={selectedSymbol}
                  onChange={handleStockSelect}
                  className="form-select"
                  required
                >
                  <option value="">{t('portfolio.alerts.select_option')}</option>
                  {userHoldings.map((holding) => (
                    <option key={holding.symbol} value={holding.symbol}>
                      {holding.symbol} - {holding.name || holding.company_name || 'N/A'} ({holding.shares} {t('portfolio.performance.shares_label')})
                    </option>
                  ))}
                </select>
              </div>

              {/* Show Company Name as read-only when stock is selected */}
              {formData.symbol && (
                <div className="form-group">
                  <label>{t('portfolio.alerts.company_name_label')}</label>
                  <input
                    type="text"
                    value={formData.companyName}
                    readOnly
                    className="form-input"
                    style={{
                      backgroundColor: '#f3f4f6',
                      cursor: 'not-allowed',
                      color: '#374151'
                    }}
                  />
                  <small style={{ color: '#6b7280', fontSize: '0.75rem' }}>
                    {t('portfolio.alerts.auto_filled_hint')}
                  </small>
                </div>
              )}

              {editingAlert && !selectedSymbol && (
                <div className="alert alert-info" style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#d1ecf1', border: '1px solid #bee5eb', borderRadius: '0.25rem', color: '#0c5460' }}>
                  {t('portfolio.alerts.alert_not_in_holdings', { symbol: formData.symbol })}
                </div>
              )}

              {/* Manual entry fields only shown when editing an alert for a stock not in holdings */}
              {editingAlert && !selectedSymbol && (
                <>
                  <div className="form-group">
                    <label>{t('portfolio.alerts.symbol_label')}</label>
                    <input
                      type="text"
                      value={formData.symbol}
                      readOnly
                      style={{ backgroundColor: '#f3f4f6', cursor: 'not-allowed' }}
                    />
                  </div>
                  <div className="form-group">
                    <label>{t('portfolio.alerts.company_name_label')}</label>
                    <input
                      type="text"
                      value={formData.companyName}
                      onChange={(e) => setFormData({...formData, companyName: e.target.value})}
                      placeholder={t('portfolio.alerts.company_name_label')}
                    />
                  </div>
                </>
              )}
              <div className="form-group">
                <label>{t('portfolio.alerts.alert_type_label')}</label>
                <select
                  value={formData.alertType}
                  onChange={(e) => setFormData({...formData, alertType: e.target.value})}
                  required
                >
                  <option value="price_above">{t('portfolio.alerts.price_above_option')}</option>
                  <option value="price_below">{t('portfolio.alerts.price_below_option')}</option>
                </select>
              </div>
              <div className="form-group">
                <label>{t('portfolio.alerts.target_price_label')}</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.targetPrice}
                  onChange={(e) => setFormData({...formData, targetPrice: e.target.value})}
                  min="0.01"
                  required
                />
              </div>
              <div className="form-group">
                <label>{t('portfolio.alerts.notes_label')}</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({...formData, notes: e.target.value})}
                  placeholder={t('portfolio.alerts.notes_placeholder')}
                  rows="3"
                />
              </div>
              <div className="form-group checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.isActive}
                    onChange={(e) => setFormData({...formData, isActive: e.target.checked})}
                  />
                  {t('portfolio.alerts.active_alert_checkbox')}
                </label>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">
                  {editingAlert ? t('portfolio.alerts.update_button') : t('portfolio.alerts.create_button')}
                </button>
                <button type="button" onClick={resetForm} className="btn btn-secondary">
                  {t('portfolio.alerts.cancel_button')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={!!confirmDelete}
        title={t('portfolio.alerts.delete_tooltip')}
        message={t('portfolio.alerts.delete_confirm_message', { symbol: confirmDelete?.symbol })}
        onConfirm={() => handleDelete(confirmDelete.id)}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
};

export default Alerts;