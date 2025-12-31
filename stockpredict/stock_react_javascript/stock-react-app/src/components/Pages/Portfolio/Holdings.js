import React, { useState, useEffect, useCallback } from 'react';
import { LoadingSpinner, ErrorMessage, DataTable, ConfirmDialog } from '../../ui';
import { TrendingUp, TrendingDown, Plus, Trash2, DollarSign, Coins, Building2 } from 'lucide-react';
import portfolioService from '../../../services/portfolioService';
import { formatVND, formatStockPrice } from '../../../utils/currencyFormatter';
import '../../../styles/holdings.css';

const Holdings = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [summary, setSummary] = useState({ total_stocks: 0, total_value: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showSellForm, setShowSellForm] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const [formData, setFormData] = useState({
    symbol: '',
    companyName: '',
    shares: '',
    price: ''
  });

  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [sellData, setSellData] = useState({ shares: '' });
  const [stockOptions, setStockOptions] = useState([]);

  const loadStockOptions = useCallback(async () => {
    try {
      const result = await portfolioService.getStockOptions();
      if (result.success) {
        setStockOptions(result.data);
      } else {
        console.error('Failed to load stock options:', result.error);
        setStockOptions([]); // Set empty array as fallback
      }
    } catch (err) {
      console.error('Failed to load stock options:', err);
      setStockOptions([]); // Set empty array as fallback
    }
  }, []);

  const loadPortfolioData = useCallback(async () => {
    setLoading(true);
    try {
      const [portfolioResult, summaryResult] = await Promise.all([
        portfolioService.getPortfolio(),
        portfolioService.getPortfolioSummary()
      ]);

      if (portfolioResult.success) {
        setPortfolio(portfolioService.formatPortfolioData(portfolioResult.data));
      } else {
        setError('Failed to load portfolio: ' + portfolioResult.error);
      }

      if (summaryResult.success) {
        setSummary({
          total_stocks: summaryResult.data.total_stocks || 0,
          total_value: parseFloat(summaryResult.data.total_value) || 0
        });
      }
    } catch (err) {
      setError('Failed to load portfolio data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPortfolioData();
    loadStockOptions();
  }, [loadPortfolioData, loadStockOptions]);

  const handleAddStock = async (e) => {
    if (e) e.preventDefault();

    // Validate form data
    const validation = portfolioService.validateStockData(
      formData.symbol, 
      formData.shares, 
      formData.price
    );

    if (!validation.isValid) {
      setError(validation.errors.join(', '));
      return;
    }

    try {
      const result = await portfolioService.addStock(
        formData.symbol,
        formData.companyName,
        parseInt(formData.shares),
        parseFloat(formData.price)
      );

      if (result.success) {
        resetForm();
        loadPortfolioData();
        setError(null);
      } else {
        setError('Failed to add stock: ' + result.error);
      }
    } catch (err) {
      setError('Failed to add stock: ' + err.message);
    }
  };

  const handleSellStock = async (e) => {
    e.preventDefault();
    console.log('Selling stock:', selectedStock.symbol, 'shares:', sellData.shares);
    
    try {
      const result = await portfolioService.sellStock(
        selectedStock.symbol, 
        parseInt(sellData.shares)
      );

      if (result.success) {
        console.log('Stock sold successfully');
        setSellData({ shares: '' });
        setShowSellForm(false);
        setSelectedStock(null);
        loadPortfolioData();
        setError(null);
      } else {
        console.error('Failed to sell stock:', result.error);
        setError('Failed to sell stock: ' + result.error);
      }
    } catch (err) {
      console.error('Error selling stock:', err);
      setError('Failed to sell stock: ' + err.message);
    }
  };

  const handleRemoveStock = async (symbol) => {
    console.log('Removing stock with symbol:', symbol);
    try {
      const result = await portfolioService.removeStock(symbol);
      
      if (result.success) {
        console.log('Stock removed successfully');
        setConfirmDelete(null);
        loadPortfolioData();
        setError(null);
      } else {
        console.error('Failed to remove stock:', result.error);
        setError('Failed to remove stock: ' + result.error);
      }
    } catch (err) {
      console.error('Error removing stock:', err);
      setError('Failed to remove stock: ' + err.message);
    }
  };

  const openSellForm = (stock) => {
    console.log('Opening sell form for stock:', stock);
    if (!stock) {
      console.error('No stock provided to openSellForm');
      return;
    }
    setSelectedStock(stock);
    setSellData({ shares: '' });
    setShowSellForm(true);
    console.log('Sell form state updated, showSellForm:', true);
  };

  const handleStockSelect = (e) => {
    const symbol = e.target.value;
    setSelectedSymbol(symbol);
    
    if (symbol) {
      const stock = stockOptions.find(s => s.symbol === symbol);
      setFormData({
        symbol: stock.symbol,
        companyName: stock.name,
        shares: '',
        price: stock.price.toString()
      });
    } else {
      setFormData({ symbol: '', companyName: '', shares: '', price: '' });
    }
  };

  const resetForm = () => {
    setFormData({ symbol: '', companyName: '', shares: '', price: '' });
    setSelectedSymbol('');
    setShowAddForm(false);
  };

  const columns = [
    {
      key: 'symbol',
      header: 'Mã',
      render: (value) => (
        <span className="symbol-badge">
          {value}
        </span>
      )
    },
    {
      key: 'name',
      header: 'Công ty',
      render: (value) => (
        <div className="company-cell" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Building2 size={16} style={{ color: '#6366f1', opacity: 0.7 }} />
          <span>{value || 'N/A'}</span>
        </div>
      )
    },
    {
      key: 'shares',
      header: 'Số CP',
      render: (value) => (
        <span className="shares-badge">
          {value?.toLocaleString() || 0}
        </span>
      )
    },
    {
      key: 'avgPrice',
      header: 'Giá',
      render: (value) => (
        <span className="price-value">
          <Coins size={14} style={{ color: '#0d9488' }} />
          {formatStockPrice(typeof value === 'number' ? value : 0)}
        </span>
      )
    },
    {
      key: 'total_value',
      header: 'Tổng giá trị',
      render: (value, row) => (
        <span className="total-value-badge">
          <DollarSign size={14} className="currency-icon" />
          {formatVND((row.shares || 0) * (row.avgPrice || 0) * 1000)}
        </span>
      )
    },
    {
      key: 'actions',
      header: 'Thao tác',
      render: (value, row) => (
        <div className="actions-cell">
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              console.log('Sell button clicked for stock:', row);
              openSellForm(row);
            }}
            className="action-btn sell-btn"
            title="Bán cổ phiếu"
          >
            <TrendingDown size={18} />
          </button>
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              console.log('Remove button clicked for stock:', row);
              setConfirmDelete(row);
            }}
            className="action-btn remove-btn"
            title="Xóa cổ phiếu"
          >
            <Trash2 size={18} />
          </button>
        </div>
      )
    }
  ];

  if (loading) return <LoadingSpinner />;

  console.log('Holdings render - showSellForm:', showSellForm, 'selectedStock:', selectedStock);
  console.log('confirmDelete:', confirmDelete);

  return (
    <div className="holdings-page">
      <div className="page-header">
        <h1>Danh mục của tôi</h1>
        <button
          onClick={() => {
            console.log('Add Stock button clicked');
            setShowAddForm(true);
          }}
          className="btn btn-primary"
        >
          <Plus size={16} />
          Thêm cổ phiếu
        </button>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <div className="portfolio-summary">
        <div className="summary-card">
          <div className="summary-item">
            <DollarSign className="summary-icon" />
            <div>
              <h3>Tổng giá trị</h3>
              <p className="summary-value">{formatVND(typeof summary.total_value === 'number' ? summary.total_value * 1000 : 0)}</p>
            </div>
          </div>
          <div className="summary-item">
            <TrendingUp className="summary-icon" />
            <div>
              <h3>Tổng số cổ phiếu</h3>
              <p className="summary-value">{summary.total_stocks || 0}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="portfolio-table">
        <DataTable
          data={portfolio}
          columns={columns}
          emptyMessage="Chưa có cổ phiếu trong danh mục"
        />
      </div>

      {showAddForm && (
        <div className="modal-overlay" style={{ display: 'flex', position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.5)', zIndex: 999999, alignItems: 'center', justifyContent: 'center' }}>
          <div className="modal" style={{ display: 'block', backgroundColor: 'white', padding: '2rem', borderRadius: '0.5rem', minWidth: '500px', maxWidth: '600px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)', position: 'relative' }}>
            <div className="modal-header">
              <h2>Thêm cổ phiếu vào danh mục</h2>
              <button onClick={resetForm} className="modal-close">
                ×
              </button>
            </div>

            <div>
              <div className="stock-select-container">
                <label className="form-label">Chọn cổ phiếu</label>
                <select
                  value={selectedSymbol}
                  onChange={handleStockSelect}
                  className="form-select"
                >
                  <option value="">-- Chọn một cổ phiếu --</option>
                  {stockOptions.map((stock) => (
                    <option key={stock.symbol} value={stock.symbol}>
                      {stock.symbol} - {stock.name} ({formatStockPrice(stock.price)})
                    </option>
                  ))}
                </select>
              </div>

              {formData.symbol && (
                <div className="stock-info-card">
                  <h3>{formData.symbol} - {formData.companyName}</h3>
                  <p>Giá hiện tại: <strong>{formatStockPrice(formData.price)}</strong></p>
                </div>
              )}

              {formData.symbol && (
                <div className="shares-input-container">
                  <label className="form-label">Số lượng cổ phiếu</label>
                  <input
                    type="number"
                    value={formData.shares}
                    onChange={(e) => setFormData({...formData, shares: e.target.value})}
                    min="1"
                    placeholder="Nhập số lượng cổ phiếu"
                    className="form-input"
                  />
                </div>
              )}

              {formData.shares && formData.price && (
                <div className="total-cost-card">
                  <p>Tổng chi phí: {formatVND(portfolioService.calculateTotalCost(formData.shares, formData.price) * 1000)}</p>
                </div>
              )}

              <div className="form-actions">
                <button onClick={resetForm} className="btn btn-secondary">
                  Hủy
                </button>

                {formData.symbol && formData.shares && (
                  <button onClick={handleAddStock} className="btn btn-primary">
                    Thêm vào danh mục
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {showSellForm && selectedStock && (
        <div className="modal-overlay" style={{ display: 'flex', position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.5)', zIndex: 999999, alignItems: 'center', justifyContent: 'center' }}>
          <div className="modal" style={{ display: 'block', backgroundColor: 'white', padding: '2rem', borderRadius: '0.5rem', minWidth: '500px', maxWidth: '600px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)', position: 'relative' }}>
            <div className="modal-header">
              <h2>Bán {selectedStock.symbol}</h2>
              <button onClick={() => setShowSellForm(false)} className="modal-close">×</button>
            </div>
            <form onSubmit={handleSellStock} className="stock-form">
              <div className="form-group">
                <label>Số cổ phiếu khả dụng: {selectedStock.shares}</label>
                <input
                  type="number"
                  value={sellData.shares}
                  onChange={(e) => setSellData({shares: e.target.value})}
                  min="1"
                  max={selectedStock.shares}
                  required
                  placeholder="Số cổ phiếu cần bán"
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-danger">
                  Bán cổ phiếu
                </button>
                <button type="button" onClick={() => setShowSellForm(false)} className="btn btn-secondary">
                  Hủy
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmDialog
        show={!!confirmDelete}
        title="Xóa cổ phiếu"
        message={`Bạn có chắc muốn xóa ${confirmDelete?.symbol} khỏi danh mục?`}
        onConfirm={() => handleRemoveStock(confirmDelete.symbol)}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
};

export default Holdings;