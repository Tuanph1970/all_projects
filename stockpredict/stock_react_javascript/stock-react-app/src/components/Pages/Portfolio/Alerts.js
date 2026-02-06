import React, { useState, useEffect } from 'react';
import { LoadingSpinner, ErrorMessage, DataTable, ConfirmDialog } from '../../ui';
import { Bell, BellOff, Plus, Trash2, Edit, TrendingUp, TrendingDown, Calendar } from 'lucide-react';
import { alertsAPI, stockAPI } from '../../../services/api';
import portfolioService from '../../../services/portfolioService';
import { formatStockPrice } from '../../../utils/currencyFormatter';
import '../../../styles/alerts.css';

const Alerts = () => {
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
      setError('Failed to fetch alerts');
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
      setError(err.message || 'Failed to save alert');
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
      setError(err.message || 'Failed to delete alert');
    }
  };

  const toggleAlert = async (id) => {
    try {
      await alertsAPI.toggleAlert(id);
      // Refresh alerts list
      await fetchAlerts();
    } catch (err) {
      setError(err.message || 'Failed to toggle alert');
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
      header: 'Mã CP',
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
      header: 'Loại cảnh báo',
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
          {value === 'price_above' ? 'Giá trên' : 'Giá dưới'}
        </div>
      )
    },
    {
      key: 'targetPrice',
      header: 'Giá mục tiêu',
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
          {formatStockPrice(typeof value === 'number' ? value : 0)}
        </span>
      )
    },
    {
      key: 'currentPrice',
      header: 'Giá hiện tại',
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
          {formatStockPrice(typeof value === 'number' ? value : 0)}
        </span>
      )
    },
    {
      key: 'status',
      header: 'Trạng thái',
      render: (_, alert) => {
        const status = getAlertStatus(alert);
        const statusLabels = {
          'triggered': 'Kích hoạt',
          'active': 'Hoạt động',
          'inactive': 'Không hoạt động'
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
      header: 'Ngày tạo',
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
      header: 'Thao tác',
      render: (_, alert) => (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => toggleAlert(alert.id)}
            className={`action-btn ${alert.isActive ? 'active-btn' : 'inactive-btn'}`}
            title={alert.isActive ? 'Hủy kích hoạt cảnh báo' : 'Kích hoạt cảnh báo'}
          >
            {alert.isActive ? <Bell size={18} /> : <BellOff size={18} />}
          </button>
          <button
            onClick={() => handleEdit(alert)}
            className="action-btn edit-btn"
            title="Chỉnh sửa cảnh báo"
          >
            <Edit size={18} />
          </button>
          <button
            onClick={() => setConfirmDelete(alert)}
            className="action-btn remove-btn"
            title="Xóa cảnh báo"
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
        <h1>Cảnh báo giá</h1>
        <button
          onClick={() => setShowAddForm(true)}
          className="btn btn-primary"
        >
          <Plus size={16} />
          Tạo cảnh báo
        </button>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <div className="alerts-summary">
        <div className="summary-stats">
          <div className="stat-item">
            <span className="stat-value">{alerts.filter(a => a.isActive).length}</span>
            <span className="stat-label">Cảnh báo hoạt động</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{alerts.filter(a => getAlertStatus(a) === 'triggered').length}</span>
            <span className="stat-label">Đã kích hoạt</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{alerts.length}</span>
            <span className="stat-label">Tổng cảnh báo</span>
          </div>
        </div>
      </div>

      <div className="alerts-table">
        <DataTable
          data={alerts}
          columns={columns}
          emptyMessage="Chưa có cảnh báo giá nào được tạo"
        />
      </div>

      {showAddForm && (
        <div className="modal-overlay" onClick={resetForm} style={{ display: 'flex', position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.5)', zIndex: 999999, alignItems: 'center', justifyContent: 'center' }}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ display: 'block', backgroundColor: 'white', padding: '2rem', borderRadius: '0.5rem', minWidth: '500px', maxWidth: '600px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)', position: 'relative' }}>
            <div className="modal-header">
              <h2>{editingAlert ? 'Chỉnh sửa cảnh báo' : 'Tạo cảnh báo giá'}</h2>
              <button onClick={resetForm} className="modal-close">×</button>
            </div>
            <form onSubmit={handleSubmit} className="alert-form">
              <div className="form-group">
                <label>Chọn cổ phiếu</label>
                <select
                  value={selectedSymbol}
                  onChange={handleStockSelect}
                  className="form-select"
                  required
                >
                  <option value="">-- Chọn từ danh mục của bạn --</option>
                  {userHoldings.map((holding) => (
                    <option key={holding.symbol} value={holding.symbol}>
                      {holding.symbol} - {holding.name || holding.company_name || 'N/A'} ({holding.shares} cổ phiếu)
                    </option>
                  ))}
                </select>
              </div>

              {/* Show Company Name as read-only when stock is selected */}
              {formData.symbol && (
                <div className="form-group">
                  <label>Tên công ty</label>
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
                    Tự động điền từ cổ phiếu được chọn
                  </small>
                </div>
              )}

              {editingAlert && !selectedSymbol && (
                <div className="alert alert-info" style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#d1ecf1', border: '1px solid #bee5eb', borderRadius: '0.25rem', color: '#0c5460' }}>
                  <strong>Lưu ý:</strong> Cảnh báo này dành cho cổ phiếu ({formData.symbol}) hiện không có trong danh mục của bạn.
                  Bạn vẫn có thể chỉnh sửa cảnh báo, nhưng không thể chọn nó từ danh sách thả xuống.
                </div>
              )}

              {/* Manual entry fields only shown when editing an alert for a stock not in holdings */}
              {editingAlert && !selectedSymbol && (
                <>
                  <div className="form-group">
                    <label>Mã cổ phiếu</label>
                    <input
                      type="text"
                      value={formData.symbol}
                      readOnly
                      style={{ backgroundColor: '#f3f4f6', cursor: 'not-allowed' }}
                    />
                  </div>
                  <div className="form-group">
                    <label>Tên công ty</label>
                    <input
                      type="text"
                      value={formData.companyName}
                      onChange={(e) => setFormData({...formData, companyName: e.target.value})}
                      placeholder="Nhập tên công ty"
                    />
                  </div>
                </>
              )}
              <div className="form-group">
                <label>Loại cảnh báo</label>
                <select
                  value={formData.alertType}
                  onChange={(e) => setFormData({...formData, alertType: e.target.value})}
                  required
                >
                  <option value="price_above">Giá trên</option>
                  <option value="price_below">Giá dưới</option>
                </select>
              </div>
              <div className="form-group">
                <label>Giá mục tiêu</label>
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
                <label>Ghi chú (Tùy chọn)</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({...formData, notes: e.target.value})}
                  placeholder="Thêm ghi chú về cảnh báo này..."
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
                  Cảnh báo hoạt động
                </label>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">
                  {editingAlert ? 'Cập nhật cảnh báo' : 'Tạo cảnh báo'}
                </button>
                <button type="button" onClick={resetForm} className="btn btn-secondary">
                  Hủy
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={!!confirmDelete}
        title="Xóa cảnh báo"
        message={`Bạn có chắc chắn muốn xóa cảnh báo cho ${confirmDelete?.symbol}?`}
        onConfirm={() => handleDelete(confirmDelete.id)}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
};

export default Alerts;