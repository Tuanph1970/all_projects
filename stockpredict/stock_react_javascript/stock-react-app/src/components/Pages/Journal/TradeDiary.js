import React, { useState, useEffect, useCallback } from 'react';
import { LoadingSpinner, ErrorMessage, ConfirmDialog } from '../../ui';
import {
  BookOpen, Plus, Save, Trash2, Upload, Image, X,
  TrendingUp, TrendingDown, Clock, CheckCircle, Lock,
  ChevronDown, ChevronRight, AlertTriangle, Heart, Brain
} from 'lucide-react';
import journalService from '../../../services/journalService';
import '../../../styles/journal.css';

const CHART_PATTERNS = [
  { value: 'Head and Shoulders', label: 'Head and Shoulders' },
  { value: 'Inverse Head and Shoulders', label: 'Inverse H&S' },
  { value: 'Double Top', label: 'Double Top' },
  { value: 'Double Bottom', label: 'Double Bottom' },
  { value: 'Triple Top', label: 'Triple Top' },
  { value: 'Triple Bottom', label: 'Triple Bottom' },
  { value: 'Ascending Triangle', label: 'Ascending Triangle' },
  { value: 'Descending Triangle', label: 'Descending Triangle' },
  { value: 'Symmetrical Triangle', label: 'Symmetrical Triangle' },
  { value: 'Bull Flag', label: 'Bull Flag' },
  { value: 'Bear Flag', label: 'Bear Flag' },
  { value: 'Cup and Handle', label: 'Cup and Handle' },
  { value: 'Rising Wedge', label: 'Rising Wedge' },
  { value: 'Falling Wedge', label: 'Falling Wedge' },
  { value: 'Channel Up', label: 'Channel Up' },
  { value: 'Channel Down', label: 'Channel Down' },
  { value: 'Breakout', label: 'Breakout' },
  { value: 'Breakdown', label: 'Breakdown' },
  { value: 'Consolidation', label: 'Consolidation' },
  { value: 'Other', label: 'Khác' }
];

const EMOTIONAL_STATES = [
  { value: 'Confident', label: 'Tự tin', emoji: '💪' },
  { value: 'Calm', label: 'Bình tĩnh', emoji: '😌' },
  { value: 'Excited', label: 'Hưng phấn', emoji: '🤩' },
  { value: 'Anxious', label: 'Lo lắng', emoji: '😰' },
  { value: 'Fearful', label: 'Sợ hãi', emoji: '😨' },
  { value: 'Greedy', label: 'Tham lam', emoji: '🤑' },
  { value: 'Frustrated', label: 'Nản chí', emoji: '😤' },
  { value: 'Revenge', label: 'Trả thù', emoji: '😡' },
  { value: 'Bored', label: 'Chán nản', emoji: '😐' },
  { value: 'Neutral', label: 'Bình thường', emoji: '😊' }
];

const CHART_TYPES = [
  { value: 'Entry', label: 'Khi vào lệnh' },
  { value: 'During', label: 'Trong lệnh' },
  { value: 'Exit', label: 'Khi thoát lệnh' },
  { value: 'Overview', label: 'Tổng quan' }
];

const TradeDiary = () => {
  // Account & trade selection
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [trades, setTrades] = useState([]);
  const [selectedTradeId, setSelectedTradeId] = useState(null);
  const [selectedTrade, setSelectedTrade] = useState(null);

  // Diary data
  const [diary, setDiary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingDiary, setLoadingDiary] = useState(false);
  const [error, setError] = useState(null);
  const [saveMsg, setSaveMsg] = useState(null);

  // Diary form
  const [diaryForm, setDiaryForm] = useState({
    reasons_for_trade: '',
    chart_pattern: '',
    emotional_state_entry: '',
    how_it_turned_out: '',
    lessons_and_mistakes: '',
    emotional_state_during: '',
    emotional_state_exit: ''
  });

  // Chart upload
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadCaption, setUploadCaption] = useState('');
  const [uploadChartType, setUploadChartType] = useState('');
  const [uploading, setUploading] = useState(false);

  // UI
  const [expandedSection, setExpandedSection] = useState('pillar1');
  const [confirmDeleteChart, setConfirmDeleteChart] = useState(null);

  // =========================================================================
  // Load Data
  // =========================================================================

  const loadAccounts = useCallback(async () => {
    const result = await journalService.getAccounts();
    if (result.success) {
      setAccounts(result.data);
      if (result.data.length > 0 && !selectedAccountId) {
        setSelectedAccountId(result.data[0].id);
      }
    }
  }, [selectedAccountId]);

  const loadTrades = useCallback(async () => {
    if (!selectedAccountId) return;
    setLoading(true);
    try {
      const result = await journalService.getTrades(selectedAccountId, { limit: 200 });
      if (result.success) {
        setTrades(result.data.trades || []);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedAccountId]);

  const loadDiary = useCallback(async () => {
    if (!selectedTradeId) return;
    setLoadingDiary(true);
    setError(null);
    try {
      const result = await journalService.getDiary(selectedTradeId);
      if (result.success) {
        setDiary(result.data);
        setDiaryForm({
          reasons_for_trade: result.data.reasons_for_trade || '',
          chart_pattern: result.data.chart_pattern || '',
          emotional_state_entry: result.data.emotional_state_entry || '',
          how_it_turned_out: result.data.how_it_turned_out || '',
          lessons_and_mistakes: result.data.lessons_and_mistakes || '',
          emotional_state_during: result.data.emotional_state_during || '',
          emotional_state_exit: result.data.emotional_state_exit || ''
        });
      } else {
        // No diary yet
        setDiary(null);
        setDiaryForm({
          reasons_for_trade: '',
          chart_pattern: '',
          emotional_state_entry: '',
          how_it_turned_out: '',
          lessons_and_mistakes: '',
          emotional_state_during: '',
          emotional_state_exit: ''
        });
      }
    } catch (err) {
      setError('Lỗi tải nhật ký');
    } finally {
      setLoadingDiary(false);
    }
  }, [selectedTradeId]);

  useEffect(() => { loadAccounts(); }, [loadAccounts]);
  useEffect(() => { loadTrades(); }, [loadTrades]);
  useEffect(() => { loadDiary(); }, [loadDiary]);

  useEffect(() => {
    if (selectedTradeId && trades.length > 0) {
      setSelectedTrade(trades.find(t => t.id === selectedTradeId) || null);
    } else {
      setSelectedTrade(null);
    }
  }, [selectedTradeId, trades]);

  // =========================================================================
  // Diary Actions
  // =========================================================================

  const handleCreateDiary = async () => {
    if (!selectedTradeId) return;
    const data = {};
    if (diaryForm.reasons_for_trade) data.reasons_for_trade = diaryForm.reasons_for_trade;
    if (diaryForm.chart_pattern) data.chart_pattern = diaryForm.chart_pattern;
    if (diaryForm.emotional_state_entry) data.emotional_state_entry = diaryForm.emotional_state_entry;

    const result = await journalService.createOrGetDiary(selectedTradeId, data);
    if (result.success) {
      setDiary(result.data);
      setSaveMsg('Nhật ký đã được tạo');
      setTimeout(() => setSaveMsg(null), 3000);
    } else {
      setError(result.error?.detail || result.error?.message || 'Lỗi tạo nhật ký');
    }
  };

  const handleSaveDiary = async () => {
    if (!selectedTradeId || !diary) return;
    setSaveMsg(null);
    setError(null);

    const update = {};
    // Pillar 1 fields (always editable)
    if (diaryForm.reasons_for_trade !== (diary.reasons_for_trade || ''))
      update.reasons_for_trade = diaryForm.reasons_for_trade || null;
    if (diaryForm.chart_pattern !== (diary.chart_pattern || ''))
      update.chart_pattern = diaryForm.chart_pattern || null;
    if (diaryForm.emotional_state_entry !== (diary.emotional_state_entry || ''))
      update.emotional_state_entry = diaryForm.emotional_state_entry || null;

    // Pillar 2 & 3 fields (only after trade closed)
    if (diaryForm.how_it_turned_out !== (diary.how_it_turned_out || ''))
      update.how_it_turned_out = diaryForm.how_it_turned_out || null;
    if (diaryForm.lessons_and_mistakes !== (diary.lessons_and_mistakes || ''))
      update.lessons_and_mistakes = diaryForm.lessons_and_mistakes || null;
    if (diaryForm.emotional_state_during !== (diary.emotional_state_during || ''))
      update.emotional_state_during = diaryForm.emotional_state_during || null;
    if (diaryForm.emotional_state_exit !== (diary.emotional_state_exit || ''))
      update.emotional_state_exit = diaryForm.emotional_state_exit || null;

    if (Object.keys(update).length === 0) {
      setSaveMsg('Không có thay đổi');
      setTimeout(() => setSaveMsg(null), 2000);
      return;
    }

    const result = await journalService.updateDiary(selectedTradeId, update);
    if (result.success) {
      setDiary(result.data);
      setSaveMsg('Đã lưu nhật ký');
      setTimeout(() => setSaveMsg(null), 3000);
    } else {
      setError(result.error?.detail || result.error?.message || 'Lỗi lưu nhật ký');
    }
  };

  // =========================================================================
  // Chart Upload
  // =========================================================================

  const handleUploadChart = async () => {
    if (!uploadFile || !diary) return;
    setUploading(true);
    setError(null);

    const result = await journalService.uploadDiaryChart(
      diary.id, uploadFile, uploadCaption || null, uploadChartType || null
    );

    if (result.success) {
      setUploadFile(null);
      setUploadCaption('');
      setUploadChartType('');
      loadDiary(); // Refresh to get updated charts
    } else {
      setError(result.error?.detail || result.error?.message || 'Lỗi upload ảnh');
    }
    setUploading(false);
  };

  const handleDeleteChart = async () => {
    if (!confirmDeleteChart) return;
    await journalService.deleteDiaryChart(confirmDeleteChart.id);
    setConfirmDeleteChart(null);
    loadDiary();
  };

  // =========================================================================
  // Helpers
  // =========================================================================

  const isTradeOpen = selectedTrade && selectedTrade.status === 'Open';
  const isTradeClosed = selectedTrade && selectedTrade.status === 'Closed';

  const toggleSection = (section) => {
    setExpandedSection(prev => prev === section ? null : section);
  };

  const getEmotionLabel = (value) => {
    const state = EMOTIONAL_STATES.find(s => s.value === value);
    return state ? `${state.emoji} ${state.label}` : value;
  };

  // =========================================================================
  // Render
  // =========================================================================

  if (accounts.length === 0 && !loading) {
    return (
      <div className="journal-accounts">
        <div className="journal-empty">
          <BookOpen size={48} strokeWidth={1} />
          <h3>Chưa có tài khoản</h3>
          <p>Vui lòng tạo tài khoản nhật ký trước.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="trade-diary">
      {/* Header */}
      <div className="journal-header">
        <div className="journal-title">
          <BookOpen size={24} />
          <h2>Nhật ký giao dịch</h2>
        </div>
        <div className="trade-log-actions">
          <select
            className="account-selector"
            value={selectedAccountId || ''}
            onChange={e => {
              setSelectedAccountId(parseInt(e.target.value));
              setSelectedTradeId(null);
              setDiary(null);
            }}
          >
            {accounts.map(a => (
              <option key={a.id} value={a.id}>{a.account_name}</option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadDiary} />}
      {saveMsg && (
        <div className="diary-save-msg">
          <CheckCircle size={14} /> {saveMsg}
        </div>
      )}

      <div className="diary-layout">
        {/* Left: Trade List */}
        <div className="diary-trade-list">
          <h3 className="diary-section-title">Giao dịch</h3>
          {loading ? (
            <LoadingSpinner text="Đang tải..." />
          ) : trades.length === 0 ? (
            <p className="diary-empty-hint">Chưa có giao dịch nào.</p>
          ) : (
            <div className="diary-trade-items">
              {trades.map(trade => (
                <button
                  key={trade.id}
                  className={`diary-trade-item ${selectedTradeId === trade.id ? 'active' : ''}`}
                  onClick={() => setSelectedTradeId(trade.id)}
                >
                  <div className="diary-trade-item-header">
                    <span className="diary-trade-num">#{trade.trade_number}</span>
                    <span className={`direction-badge direction-${trade.direction.toLowerCase()}`}>
                      {trade.direction === 'Long' ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                      {trade.direction}
                    </span>
                  </div>
                  <div className="diary-trade-item-body">
                    <strong>{trade.market_ticker}</strong>
                    <span className={`status-badge status-${trade.status.toLowerCase()}`}>
                      {trade.status === 'Open' ? <Clock size={10} /> : <CheckCircle size={10} />}
                      {trade.status === 'Open' ? 'Mở' : trade.status === 'Closed' ? 'Đóng' : 'Hủy'}
                    </span>
                  </div>
                  <div className="diary-trade-item-date">{trade.entry_date}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Diary Content */}
        <div className="diary-content">
          {!selectedTradeId ? (
            <div className="diary-empty-content">
              <BookOpen size={36} strokeWidth={1} />
              <p>Chọn một giao dịch để xem/viết nhật ký</p>
            </div>
          ) : loadingDiary ? (
            <LoadingSpinner text="Đang tải nhật ký..." />
          ) : (
            <>
              {/* Trade Info Bar */}
              {selectedTrade && (
                <div className="diary-trade-info">
                  <span>#{selectedTrade.trade_number}</span>
                  <strong>{selectedTrade.market_ticker}</strong>
                  <span className={`direction-badge direction-${selectedTrade.direction.toLowerCase()}`}>
                    {selectedTrade.direction}
                  </span>
                  <span>Giá vào: {selectedTrade.entry_price?.toLocaleString()}</span>
                  {selectedTrade.exit_price && <span>Giá thoát: {selectedTrade.exit_price?.toLocaleString()}</span>}
                  {selectedTrade.net_pnl != null && (
                    <span className={selectedTrade.net_pnl >= 0 ? 'text-profit' : 'text-loss'}>
                      P/L: {selectedTrade.net_pnl?.toLocaleString()}
                    </span>
                  )}
                </div>
              )}

              {/* No Diary Yet */}
              {!diary && (
                <div className="diary-create-section">
                  <h3>Chưa có nhật ký cho giao dịch này</h3>
                  <p>Tạo nhật ký theo phương pháp 3 trụ cột của Schwager.</p>
                  <button className="btn-primary" onClick={handleCreateDiary}>
                    <Plus size={16} /> Tạo nhật ký
                  </button>
                </div>
              )}

              {/* Diary Form — 3 Pillars */}
              {diary && (
                <div className="diary-pillars">
                  {/* Pillar 1: Reasons for Trade (always editable) */}
                  <div className={`diary-pillar ${expandedSection === 'pillar1' ? 'expanded' : ''}`}>
                    <button className="pillar-header" onClick={() => toggleSection('pillar1')}>
                      <div className="pillar-header-left">
                        <Brain size={18} className="pillar-icon pillar-icon-1" />
                        <h4>Trụ 1: Lý do vào lệnh</h4>
                      </div>
                      {expandedSection === 'pillar1' ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>
                    {expandedSection === 'pillar1' && (
                      <div className="pillar-body">
                        <div className="form-group">
                          <label>Lý do vào lệnh</label>
                          <textarea
                            value={diaryForm.reasons_for_trade}
                            onChange={e => setDiaryForm({ ...diaryForm, reasons_for_trade: e.target.value })}
                            rows={4}
                            placeholder="Phân tích kỹ thuật, tín hiệu, setup pattern, xúc tác..."
                          />
                        </div>
                        <div className="form-row">
                          <div className="form-group">
                            <label>Mẫu hình kỹ thuật</label>
                            <select
                              value={diaryForm.chart_pattern}
                              onChange={e => setDiaryForm({ ...diaryForm, chart_pattern: e.target.value })}
                            >
                              <option value="">— Chọn —</option>
                              {CHART_PATTERNS.map(p => (
                                <option key={p.value} value={p.value}>{p.label}</option>
                              ))}
                            </select>
                          </div>
                          <div className="form-group">
                            <label>Tâm lý khi vào lệnh</label>
                            <select
                              value={diaryForm.emotional_state_entry}
                              onChange={e => setDiaryForm({ ...diaryForm, emotional_state_entry: e.target.value })}
                            >
                              <option value="">— Chọn —</option>
                              {EMOTIONAL_STATES.map(s => (
                                <option key={s.value} value={s.value}>{s.emoji} {s.label}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Pillar 2: How It Turned Out (locked until trade closed) */}
                  <div className={`diary-pillar ${expandedSection === 'pillar2' ? 'expanded' : ''} ${isTradeOpen ? 'pillar-locked' : ''}`}>
                    <button className="pillar-header" onClick={() => toggleSection('pillar2')}>
                      <div className="pillar-header-left">
                        <Heart size={18} className="pillar-icon pillar-icon-2" />
                        <h4>Trụ 2: Kết quả giao dịch</h4>
                        {isTradeOpen && <Lock size={14} className="pillar-lock" />}
                      </div>
                      {expandedSection === 'pillar2' ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>
                    {expandedSection === 'pillar2' && (
                      <div className="pillar-body">
                        {isTradeOpen && (
                          <div className="pillar-lock-notice">
                            <Lock size={14} />
                            <span>Theo phương pháp Schwager: phần này chỉ điền sau khi đóng lệnh</span>
                          </div>
                        )}
                        <div className="form-group">
                          <label>Giao dịch diễn ra như thế nào?</label>
                          <textarea
                            value={diaryForm.how_it_turned_out}
                            onChange={e => setDiaryForm({ ...diaryForm, how_it_turned_out: e.target.value })}
                            rows={4}
                            placeholder="Mô tả diễn biến giao dịch..."
                            disabled={isTradeOpen}
                          />
                        </div>
                        <div className="form-group">
                          <label>Tâm lý trong quá trình giao dịch</label>
                          <select
                            value={diaryForm.emotional_state_during}
                            onChange={e => setDiaryForm({ ...diaryForm, emotional_state_during: e.target.value })}
                            disabled={isTradeOpen}
                          >
                            <option value="">— Chọn —</option>
                            {EMOTIONAL_STATES.map(s => (
                              <option key={s.value} value={s.value}>{s.emoji} {s.label}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Pillar 3: Lessons & Mistakes (locked until trade closed) */}
                  <div className={`diary-pillar ${expandedSection === 'pillar3' ? 'expanded' : ''} ${isTradeOpen ? 'pillar-locked' : ''}`}>
                    <button className="pillar-header" onClick={() => toggleSection('pillar3')}>
                      <div className="pillar-header-left">
                        <AlertTriangle size={18} className="pillar-icon pillar-icon-3" />
                        <h4>Trụ 3: Bài học & Sai lầm</h4>
                        {isTradeOpen && <Lock size={14} className="pillar-lock" />}
                      </div>
                      {expandedSection === 'pillar3' ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>
                    {expandedSection === 'pillar3' && (
                      <div className="pillar-body">
                        {isTradeOpen && (
                          <div className="pillar-lock-notice">
                            <Lock size={14} />
                            <span>Theo phương pháp Schwager: phần này chỉ điền sau khi đóng lệnh</span>
                          </div>
                        )}
                        <div className="form-group">
                          <label>Bài học và sai lầm</label>
                          <textarea
                            value={diaryForm.lessons_and_mistakes}
                            onChange={e => setDiaryForm({ ...diaryForm, lessons_and_mistakes: e.target.value })}
                            rows={4}
                            placeholder="Bạn đã học được gì? Sai lầm nào cần tránh?..."
                            disabled={isTradeOpen}
                          />
                        </div>
                        <div className="form-group">
                          <label>Tâm lý khi thoát lệnh</label>
                          <select
                            value={diaryForm.emotional_state_exit}
                            onChange={e => setDiaryForm({ ...diaryForm, emotional_state_exit: e.target.value })}
                            disabled={isTradeOpen}
                          >
                            <option value="">— Chọn —</option>
                            {EMOTIONAL_STATES.map(s => (
                              <option key={s.value} value={s.value}>{s.emoji} {s.label}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Save Button */}
                  <div className="diary-save-bar">
                    <button className="btn-primary" onClick={handleSaveDiary}>
                      <Save size={16} /> Lưu nhật ký
                    </button>
                    {diary.diary_complete && (
                      <span className="diary-complete-badge">
                        <CheckCircle size={14} /> Nhật ký hoàn chỉnh
                      </span>
                    )}
                  </div>

                  {/* Chart Upload Section */}
                  <div className="diary-pillar expanded">
                    <div className="pillar-header" style={{ cursor: 'default' }}>
                      <div className="pillar-header-left">
                        <Image size={18} className="pillar-icon pillar-icon-chart" />
                        <h4>Ảnh chụp biểu đồ</h4>
                      </div>
                    </div>
                    <div className="pillar-body">
                      {/* Existing Charts */}
                      {diary.charts && diary.charts.length > 0 && (
                        <div className="diary-charts-grid">
                          {diary.charts.map(chart => (
                            <div key={chart.id} className="diary-chart-card">
                              <div className="diary-chart-img-wrapper">
                                <img
                                  src={chart.image_path}
                                  alt={chart.caption || 'Chart'}
                                  onError={e => { e.target.style.display = 'none'; }}
                                />
                              </div>
                              <div className="diary-chart-info">
                                {chart.chart_type && (
                                  <span className="diary-chart-type">{chart.chart_type}</span>
                                )}
                                {chart.caption && <span className="diary-chart-caption">{chart.caption}</span>}
                              </div>
                              <button
                                className="btn-icon btn-danger diary-chart-delete"
                                onClick={() => setConfirmDeleteChart(chart)}
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Upload Form */}
                      <div className="diary-upload-form">
                        <div className="form-row">
                          <div className="form-group flex-2">
                            <label>Chọn ảnh</label>
                            <input
                              type="file"
                              accept="image/*"
                              onChange={e => setUploadFile(e.target.files[0] || null)}
                              className="diary-file-input"
                            />
                          </div>
                          <div className="form-group">
                            <label>Loại biểu đồ</label>
                            <select
                              value={uploadChartType}
                              onChange={e => setUploadChartType(e.target.value)}
                            >
                              <option value="">— Chọn —</option>
                              {CHART_TYPES.map(t => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                        <div className="form-row">
                          <div className="form-group flex-2">
                            <label>Chú thích</label>
                            <input
                              type="text"
                              value={uploadCaption}
                              onChange={e => setUploadCaption(e.target.value)}
                              placeholder="VD: Breakout vùng kháng cự 50k..."
                            />
                          </div>
                          <div className="form-actions-inline">
                            <button
                              className="btn-primary btn-sm"
                              onClick={handleUploadChart}
                              disabled={!uploadFile || uploading}
                            >
                              <Upload size={14} /> {uploading ? 'Đang tải...' : 'Tải lên'}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Delete Chart Confirmation */}
      {confirmDeleteChart && (
        <ConfirmDialog
          title="Xóa ảnh biểu đồ"
          message="Bạn có chắc muốn xóa ảnh biểu đồ này?"
          onConfirm={handleDeleteChart}
          onCancel={() => setConfirmDeleteChart(null)}
          confirmText="Xóa"
          cancelText="Hủy"
          variant="danger"
        />
      )}
    </div>
  );
};

export default TradeDiary;
