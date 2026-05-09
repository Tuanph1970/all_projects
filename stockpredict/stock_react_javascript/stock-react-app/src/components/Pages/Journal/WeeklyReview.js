import React, { useState, useEffect, useCallback } from 'react';
import {
  CalendarRange, Plus, Save, Trash2, RefreshCw, TrendingUp,
  TrendingDown, AlertTriangle, CheckCircle, Target, Award,
  Edit3, RotateCw, DollarSign
} from 'lucide-react';
import journalService from '../../../services/journalService';
import { useNavigate } from 'react-router-dom';
import '../../../styles/journal.css';

const WeeklyReview = () => {
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [selectedReview, setSelectedReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [showNewForm, setShowNewForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // New review form
  const [weekStart, setWeekStart] = useState(getMonday(new Date()).toISOString().split('T')[0]);
  const [form, setForm] = useState({
    what_went_well: '',
    what_went_wrong: '',
    key_adjustments: '',
  });

  // Load accounts
  useEffect(() => {
    const loadAccounts = async () => {
      try {
        const res = await journalService.getAccounts();
        const data = res.data || res;
        setAccounts(Array.isArray(data) ? data : []);
        if (data.length > 0) setSelectedAccountId(data[0].id);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    };
    loadAccounts();
  }, []);

  // Load reviews
  const loadReviews = useCallback(async () => {
    if (!selectedAccountId) return;
    try {
      const res = await journalService.getWeeklyReviews(selectedAccountId);
      const data = res.data || res || [];
      setReviews(Array.isArray(data) ? data : []);
      if (data.length > 0 && !selectedReview) {
        selectReview(data[0]);
      }
    } catch { setReviews([]); }
  }, [selectedAccountId]);

  useEffect(() => {
    setSelectedReview(null);
    loadReviews();
  }, [loadReviews]);

  const selectReview = (review) => {
    setSelectedReview(review);
    setForm({
      what_went_well: review.what_went_well || '',
      what_went_wrong: review.what_went_wrong || '',
      key_adjustments: review.key_adjustments || '',
    });
    setShowNewForm(false);
    setIsEditing(false);
  };

  const handleCreate = async () => {
    if (!selectedAccountId) return;
    setSaving(true);
    setSaveMsg('');
    try {
      const res = await journalService.createWeeklyReview(selectedAccountId, {
        week_start: weekStart,
        ...form,
      });
      const data = res.data || res;
      if (data.error) {
        setSaveMsg(data.message || 'Lỗi tạo review');
      } else {
        setSaveMsg('Đã tạo weekly review!');
        setShowNewForm(false);
        await loadReviews();
        selectReview(data);
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Lỗi khi tạo!';
      setSaveMsg(msg);
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(''), 4000);
    }
  };

  const handleUpdate = async () => {
    if (!selectedReview) return;
    setSaving(true);
    setSaveMsg('');
    try {
      const res = await journalService.updateWeeklyReview(
        selectedAccountId, selectedReview.id, form
      );
      const updated = res.data || res;
      setSelectedReview(updated);
      setSaveMsg('Đã cập nhật!');
      setIsEditing(false);
      await loadReviews();
    } catch {
      setSaveMsg('Lỗi cập nhật!');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(''), 3000);
    }
  };

  const handleRecalculate = async () => {
    if (!selectedReview) return;
    try {
      const res = await journalService.recalculateWeeklyStats(
        selectedAccountId, selectedReview.id
      );
      const updated = res.data || res;
      setSelectedReview(updated);
      setSaveMsg('Đã cập nhật thống kê!');
      await loadReviews();
      setTimeout(() => setSaveMsg(''), 3000);
    } catch {
      setSaveMsg('Lỗi cập nhật thống kê!');
    }
  };

  const handleDelete = async () => {
    if (!selectedReview || !window.confirm('Xóa weekly review này?')) return;
    try {
      await journalService.deleteWeeklyReview(selectedAccountId, selectedReview.id);
      setSelectedReview(null);
      setForm({ what_went_well: '', what_went_wrong: '', key_adjustments: '' });
      await loadReviews();
    } catch { /* ignore */ }
  };

  const currency = accounts.find(a => a.id === selectedAccountId)?.currency || 'VND';
  const fmt = (v) => journalService.formatCurrency(v, currency);

  if (loading) {
    return (
      <div className="journal-accounts">
        <div className="journal-empty">
          <RefreshCw size={40} className="spin" />
          <p>Đang tải...</p>
        </div>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="journal-accounts">
        <div className="journal-empty">
          <CalendarRange size={48} />
          <h3>Chưa có tài khoản nhật ký</h3>
          <p>Vui lòng tạo tài khoản nhật ký giao dịch trước khi tổng kết tuần.</p>
          <button className="btn-primary" onClick={() => navigate('/journal-accounts')} style={{ marginTop: '12px' }}>
            <Plus size={16} /> Tạo tài khoản nhật ký
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="jweek">
      {/* Header */}
      <div className="jweek-header">
        <div className="jplan-title">
          <CalendarRange size={22} />
          <h2>Tổng Kết Tuần</h2>
        </div>
        <div className="jdash-controls">
          <select
            value={selectedAccountId || ''}
            onChange={(e) => setSelectedAccountId(Number(e.target.value))}
            className="jdash-account-select"
          >
            {accounts.map(a => (
              <option key={a.id} value={a.id}>{a.account_name}</option>
            ))}
          </select>
          <button
            className="btn-primary btn-sm"
            onClick={() => {
              setShowNewForm(true);
              setSelectedReview(null);
              setForm({ what_went_well: '', what_went_wrong: '', key_adjustments: '' });
              setWeekStart(getMonday(new Date()).toISOString().split('T')[0]);
              setIsEditing(true);
            }}
          >
            <Plus size={14} /> Tạo Review
          </button>
        </div>
      </div>

      <div className="jweek-layout">
        {/* Left: Review List */}
        <div className="jplan-sidebar">
          <h4>Danh sách review</h4>
          <div className="jplan-plan-list">
            {reviews.length === 0 ? (
              <p className="jplan-no-plans">Chưa có review nào.</p>
            ) : (
              reviews.map(r => (
                <div
                  key={r.id}
                  className={`jweek-review-item ${selectedReview?.id === r.id ? 'active' : ''}`}
                  onClick={() => selectReview(r)}
                >
                  <div className="jweek-review-item-header">
                    <CalendarRange size={14} />
                    <span>{formatWeekRange(r.week_start)}</span>
                  </div>
                  <div className="jweek-review-item-stats">
                    <span>{r.trades_taken} lệnh</span>
                    <span className={r.weekly_pnl >= 0 ? 'positive' : 'negative'}>
                      {fmt(r.weekly_pnl)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Review Detail / New Form */}
        <div className="jweek-editor">
          {showNewForm ? (
            <>
              <div className="jweek-new-header">
                <h3>Tạo Weekly Review Mới</h3>
                <div className="jweek-week-picker">
                  <label>Tuần bắt đầu (Thứ 2):</label>
                  <input
                    type="date"
                    value={weekStart}
                    onChange={(e) => setWeekStart(e.target.value)}
                    className="jplan-date-input"
                  />
                </div>
              </div>

              <ReviewSections form={form} setForm={setForm} disabled={false} />

              <div className="jplan-save-bar">
                <button className="btn-primary" onClick={handleCreate} disabled={saving}>
                  <Plus size={16} />
                  {saving ? 'Đang tạo...' : 'Tạo Review'}
                </button>
                <button className="btn-secondary" onClick={() => setShowNewForm(false)}>
                  Hủy
                </button>
                {saveMsg && (
                  <span className={`jplan-save-msg ${saveMsg.includes('Lỗi') || saveMsg.includes('Đã có') ? 'error' : 'success'}`}>
                    {saveMsg}
                  </span>
                )}
              </div>
            </>
          ) : selectedReview ? (
            <>
              {/* Stats Cards */}
              <div className="jweek-stats-header">
                <h3>Tuần {formatWeekRange(selectedReview.week_start)}</h3>
                <div className="jweek-actions">
                  {!isEditing && (
                    <button className="btn-icon" onClick={() => setIsEditing(true)} title="Chỉnh sửa">
                      <Edit3 size={16} />
                    </button>
                  )}
                  <button className="btn-icon" onClick={handleRecalculate} title="Tính lại thống kê">
                    <RotateCw size={16} />
                  </button>
                  <button className="btn-icon btn-danger" onClick={handleDelete} title="Xóa">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              <div className="jweek-stat-cards">
                <div className="jweek-stat-card">
                  <Target size={18} className="jweek-stat-icon" style={{ color: '#3b82f6' }} />
                  <div>
                    <span className="jweek-stat-label">Số lệnh</span>
                    <span className="jweek-stat-value">{selectedReview.trades_taken}</span>
                  </div>
                </div>
                <div className="jweek-stat-card">
                  <Award size={18} className="jweek-stat-icon" style={{ color: '#10b981' }} />
                  <div>
                    <span className="jweek-stat-label">Thắng</span>
                    <span className="jweek-stat-value">{selectedReview.trades_won}</span>
                  </div>
                </div>
                <div className="jweek-stat-card">
                  <Target size={18} className="jweek-stat-icon" style={{ color: '#f59e0b' }} />
                  <div>
                    <span className="jweek-stat-label">Win Rate</span>
                    <span className="jweek-stat-value">{selectedReview.win_rate || 0}%</span>
                  </div>
                </div>
                <div className="jweek-stat-card">
                  <DollarSign size={18} className="jweek-stat-icon"
                    style={{ color: selectedReview.weekly_pnl >= 0 ? '#10b981' : '#ef4444' }}
                  />
                  <div>
                    <span className="jweek-stat-label">P/L tuần</span>
                    <span className={`jweek-stat-value ${selectedReview.weekly_pnl >= 0 ? 'positive' : 'negative'}`}>
                      {fmt(selectedReview.weekly_pnl)}
                    </span>
                  </div>
                </div>
              </div>

              <ReviewSections form={form} setForm={setForm} disabled={!isEditing} />

              {isEditing && (
                <div className="jplan-save-bar">
                  <button className="btn-primary" onClick={handleUpdate} disabled={saving}>
                    <Save size={16} />
                    {saving ? 'Đang lưu...' : 'Cập nhật'}
                  </button>
                  <button className="btn-secondary" onClick={() => {
                    selectReview(selectedReview);
                    setIsEditing(false);
                  }}>
                    Hủy
                  </button>
                  {saveMsg && (
                    <span className={`jplan-save-msg ${saveMsg.includes('Lỗi') ? 'error' : 'success'}`}>
                      {saveMsg}
                    </span>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="journal-empty">
              <CalendarRange size={48} />
              <h3>Chọn một review hoặc tạo mới</h3>
              <p>Weekly review giúp bạn đánh giá và cải thiện chiến lược giao dịch mỗi tuần.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Sub-components

const ReviewSections = ({ form, setForm, disabled }) => (
  <div className="jplan-sections">
    <div className="jplan-section">
      <div className="jplan-section-header" style={{ borderLeftColor: '#10b981' }}>
        <span style={{ color: '#10b981' }}><TrendingUp size={18} /></span>
        <div>
          <h4>Điều gì đã làm tốt?</h4>
          <p>Giao dịch thành công, kỷ luật tốt, tuân thủ kế hoạch</p>
        </div>
      </div>
      <textarea
        className="jplan-textarea"
        value={form.what_went_well}
        onChange={(e) => setForm(prev => ({ ...prev, what_went_well: e.target.value }))}
        disabled={disabled}
        placeholder={disabled ? '(Chưa có nội dung)' : 'Nhập nội dung...'}
        rows={4}
      />
    </div>

    <div className="jplan-section">
      <div className="jplan-section-header" style={{ borderLeftColor: '#ef4444' }}>
        <span style={{ color: '#ef4444' }}><TrendingDown size={18} /></span>
        <div>
          <h4>Điều gì chưa tốt?</h4>
          <p>Sai lầm, vi phạm kỷ luật, cơ hội bỏ lỡ</p>
        </div>
      </div>
      <textarea
        className="jplan-textarea"
        value={form.what_went_wrong}
        onChange={(e) => setForm(prev => ({ ...prev, what_went_wrong: e.target.value }))}
        disabled={disabled}
        placeholder={disabled ? '(Chưa có nội dung)' : 'Nhập nội dung...'}
        rows={4}
      />
    </div>

    <div className="jplan-section">
      <div className="jplan-section-header" style={{ borderLeftColor: '#f59e0b' }}>
        <span style={{ color: '#f59e0b' }}><AlertTriangle size={18} /></span>
        <div>
          <h4>Điều chỉnh quan trọng</h4>
          <p>Thay đổi chiến lược, quy tắc mới, bài học áp dụng</p>
        </div>
      </div>
      <textarea
        className="jplan-textarea"
        value={form.key_adjustments}
        onChange={(e) => setForm(prev => ({ ...prev, key_adjustments: e.target.value }))}
        disabled={disabled}
        placeholder={disabled ? '(Chưa có nội dung)' : 'Nhập nội dung...'}
        rows={4}
      />
    </div>
  </div>
);

// Helpers

function getMonday(d) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  date.setDate(diff);
  return date;
}

function formatWeekRange(weekStartStr) {
  if (!weekStartStr) return '';
  const start = new Date(weekStartStr + 'T00:00:00');
  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  const fmtD = (d) => d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
  return `${fmtD(start)} — ${fmtD(end)}`;
}

export default WeeklyReview;
