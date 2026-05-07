import React, { useEffect, useState, useCallback } from 'react';
import { Star, Trash2, RefreshCw, Plus, X } from 'lucide-react';
import httpClient from '../../services/httpClient';
import { API_ENDPOINTS } from '../../constants/api';
import { useRouter } from '../../context/RouterContext';

const Watchlist = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [adding, setAdding] = useState(false);

  const { navigate } = useRouter();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await httpClient.get(API_ENDPOINTS.WATCHLIST);
    if (res.success && Array.isArray(res.data)) {
      setItems(res.data);
    } else {
      setError(res.error?.message || 'Không thể tải danh sách theo dõi');
      setItems([]);
    }
    setLoading(false);
  }, []);

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
      setError(res.error?.message || 'Không thể thêm mã');
    }
  };

  const handleRemove = async (symbol) => {
    const res = await httpClient.delete(API_ENDPOINTS.WATCHLIST_REMOVE(symbol));
    if (res.success) {
      setItems(prev => prev.filter(i => (i.symbol || i) !== symbol));
    } else {
      setError(res.error?.message || `Không thể xóa ${symbol}`);
    }
  };

  const formatPrice = (v) => {
    if (v == null) return '—';
    return new Intl.NumberFormat('vi-VN').format(v);
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
          Danh sách theo dõi
        </h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={load}
            className="btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            disabled={loading}
            aria-label="Refresh"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Làm mới
          </button>
          <button
            onClick={() => setShowAdd(s => !s)}
            className="btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            {showAdd ? <X size={16} /> : <Plus size={16} />}
            {showAdd ? 'Hủy' : 'Thêm'}
          </button>
        </div>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <label htmlFor="wl-symbol" className="visually-hidden" style={{ position: 'absolute', left: '-10000px' }}>
            Mã cổ phiếu
          </label>
          <input
            id="wl-symbol"
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            placeholder="Mã cổ phiếu (vd: FPT)"
            style={{ flex: 1, padding: 8, border: '1px solid #d1d5db', borderRadius: 6 }}
            autoFocus
            maxLength={10}
            required
          />
          <button type="submit" className="btn-primary" disabled={adding}>
            {adding ? 'Đang thêm…' : 'Lưu'}
          </button>
        </form>
      )}

      {error && (
        <div style={{ padding: 12, background: '#fee2e2', color: '#991b1b', borderRadius: 6, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {loading && items.length === 0 ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#6b7280' }}>Đang tải…</div>
      ) : items.length === 0 ? (
        <div style={{ padding: 48, textAlign: 'center', color: '#6b7280', border: '1px dashed #d1d5db', borderRadius: 8 }}>
          <Star size={48} style={{ margin: '0 auto 12px', color: '#d1d5db' }} />
          <p>Chưa có mã nào trong danh sách theo dõi.</p>
          <p style={{ fontSize: 14 }}>Nhấn "Thêm" để bắt đầu theo dõi cổ phiếu yêu thích.</p>
        </div>
      ) : (
        <div style={{ background: '#fff', borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ background: '#f9fafb' }}>
              <tr>
                <th style={{ padding: 12, textAlign: 'left' }}>Mã</th>
                <th style={{ padding: 12, textAlign: 'left' }}>Tên</th>
                <th style={{ padding: 12, textAlign: 'right' }}>Giá hiện tại</th>
                <th style={{ padding: 12, textAlign: 'right' }}>Thay đổi</th>
                <th style={{ padding: 12, textAlign: 'center' }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const symbol = item.symbol || item;
                const changePct = item.change_percent ?? item.changePercent;
                const positive = changePct != null && changePct >= 0;
                return (
                  <tr key={symbol} style={{ borderTop: '1px solid #f3f4f6' }}>
                    <td style={{ padding: 12 }}>
                      <button
                        onClick={() => navigate(`company/${symbol}`)}
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
                      <button
                        onClick={() => handleRemove(symbol)}
                        title="Xóa khỏi danh sách"
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
