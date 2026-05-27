import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { LoadingSpinner, ErrorMessage, ConfirmDialog } from '../../ui';
import {
  BookOpen, Plus, Save, Trash2, Upload, Image,
  TrendingUp, TrendingDown, Clock, CheckCircle, Lock,
  ChevronDown, ChevronRight, AlertTriangle, Heart, Brain
} from 'lucide-react';
import journalService from '../../../services/journalService';
import { useNavigate } from 'react-router-dom';
import '../../../styles/journal.css';

const CHART_PATTERNS = [
  { value: 'Head and Shoulders', labelKey: 'journal.trade_diary.chart_head_and_shoulders' },
  { value: 'Inverse Head and Shoulders', labelKey: 'journal.trade_diary.chart_inverse_head_and_shoulders' },
  { value: 'Double Top', labelKey: 'journal.trade_diary.chart_double_top' },
  { value: 'Double Bottom', labelKey: 'journal.trade_diary.chart_double_bottom' },
  { value: 'Triple Top', labelKey: 'journal.trade_diary.chart_triple_top' },
  { value: 'Triple Bottom', labelKey: 'journal.trade_diary.chart_triple_bottom' },
  { value: 'Ascending Triangle', labelKey: 'journal.trade_diary.chart_ascending_triangle' },
  { value: 'Descending Triangle', labelKey: 'journal.trade_diary.chart_descending_triangle' },
  { value: 'Symmetrical Triangle', labelKey: 'journal.trade_diary.chart_symmetrical_triangle' },
  { value: 'Bull Flag', labelKey: 'journal.trade_diary.chart_bull_flag' },
  { value: 'Bear Flag', labelKey: 'journal.trade_diary.chart_bear_flag' },
  { value: 'Cup and Handle', labelKey: 'journal.trade_diary.chart_cup_and_handle' },
  { value: 'Rising Wedge', labelKey: 'journal.trade_diary.chart_rising_wedge' },
  { value: 'Falling Wedge', labelKey: 'journal.trade_diary.chart_falling_wedge' },
  { value: 'Channel Up', labelKey: 'journal.trade_diary.chart_channel_up' },
  { value: 'Channel Down', labelKey: 'journal.trade_diary.chart_channel_down' },
  { value: 'Breakout', labelKey: 'journal.trade_diary.chart_breakout' },
  { value: 'Breakdown', labelKey: 'journal.trade_diary.chart_breakdown' },
  { value: 'Consolidation', labelKey: 'journal.trade_diary.chart_consolidation' },
  { value: 'Other', labelKey: 'journal.trade_diary.chart_other' }
];

const EMOTIONAL_STATES = [
  { value: 'Confident', labelKey: 'journal.trade_diary.emo_confident', emoji: '💪' },
  { value: 'Calm', labelKey: 'journal.trade_diary.emo_calm', emoji: '😌' },
  { value: 'Excited', labelKey: 'journal.trade_diary.emo_excited', emoji: '🤩' },
  { value: 'Anxious', labelKey: 'journal.trade_diary.emo_anxious', emoji: '😰' },
  { value: 'Fearful', labelKey: 'journal.trade_diary.emo_fearful', emoji: '😨' },
  { value: 'Greedy', labelKey: 'journal.trade_diary.emo_greedy', emoji: '🤑' },
  { value: 'Frustrated', labelKey: 'journal.trade_diary.emo_frustrated', emoji: '😤' },
  { value: 'Revenge', labelKey: 'journal.trade_diary.emo_revenge', emoji: '😡' },
  { value: 'Bored', labelKey: 'journal.trade_diary.emo_bored', emoji: '😐' },
  { value: 'Neutral', labelKey: 'journal.trade_diary.emo_neutral', emoji: '😊' }
];

const CHART_TYPES = [
  { value: 'Entry', labelKey: 'journal.trade_diary.chart_entry' },
  { value: 'During', labelKey: 'journal.trade_diary.chart_during' },
  { value: 'Exit', labelKey: 'journal.trade_diary.chart_exit' },
  { value: 'Overview', labelKey: 'journal.trade_diary.chart_overview' }
];

const TradeDiary = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

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
      setError(t('journal.trade_diary.error_loading_diary'));
    } finally {
      setLoadingDiary(false);
    }
  }, [selectedTradeId, t]);

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
      setSaveMsg(t('journal.trade_diary.diary_created'));
      setTimeout(() => setSaveMsg(null), 3000);
    } else {
      setError(result.error?.detail || result.error?.message || t('journal.trade_diary.error_creating_diary'));
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
      setSaveMsg(t('journal.trade_diary.no_changes'));
      setTimeout(() => setSaveMsg(null), 2000);
      return;
    }

    const result = await journalService.updateDiary(selectedTradeId, update);
    if (result.success) {
      setDiary(result.data);
      setSaveMsg(t('journal.trade_diary.diary_saved'));
      setTimeout(() => setSaveMsg(null), 3000);
    } else {
      setError(result.error?.detail || result.error?.message || t('journal.trade_diary.error_saving_diary'));
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
      setError(result.error?.detail || result.error?.message || t('journal.trade_diary.error_uploading_chart'));
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
  // preserved for an upcoming closed-state UI branch
  // eslint-disable-next-line no-unused-vars
  const isTradeClosed = selectedTrade && selectedTrade.status === 'Closed';

  const toggleSection = (section) => {
    setExpandedSection(prev => prev === section ? null : section);
  };

  // eslint-disable-next-line no-unused-vars -- emoji labels for future render
  const getEmotionLabel = (value) => {
    const state = EMOTIONAL_STATES.find(s => s.value === value);
    return state ? `${state.emoji} ${t(state.labelKey)}` : value;
  };

  // =========================================================================
  // Render
  // =========================================================================

  if (accounts.length === 0 && !loading) {
    return (
      <div className="journal-accounts">
        <div className="journal-empty">
          <BookOpen size={48} strokeWidth={1} />
          <h3>{t('journal.common.no_accounts_title')}</h3>
          <p>{t('journal.trade_diary.create_account_first_hint')}</p>
          <button className="btn-primary" onClick={() => navigate('/journal-accounts')} style={{ marginTop: '12px' }}>
            <Plus size={16} /> {t('journal.common.create_account_btn')}
          </button>
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
          <h2>{t('journal.trade_diary.title')}</h2>
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
          <h3 className="diary-section-title">{t('journal.trade_diary.trades_section')}</h3>
          {loading ? (
            <LoadingSpinner text={t('journal.common.loading')} />
          ) : trades.length === 0 ? (
            <p className="diary-empty-hint">{t('journal.trade_diary.no_trades_hint')}</p>
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
                      {trade.status === 'Open' ? t('journal.trade_log.status_open') : trade.status === 'Closed' ? t('journal.trade_log.status_closed') : t('journal.trade_log.status_cancelled')}
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
              <p>{t('journal.trade_diary.select_trade_hint')}</p>
            </div>
          ) : loadingDiary ? (
            <LoadingSpinner text={t('journal.trade_diary.loading_diary')} />
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
                  <span>{t('journal.trade_log.entry_price_label')}: {selectedTrade.entry_price?.toLocaleString()}</span>
                  {selectedTrade.exit_price && <span>{t('journal.trade_log.exit_price_label')}: {selectedTrade.exit_price?.toLocaleString()}</span>}
                  {selectedTrade.net_pnl != null && (
                    <span className={selectedTrade.net_pnl >= 0 ? 'text-profit' : 'text-loss'}>
                      {t('journal.common.pnl_label')} {selectedTrade.net_pnl?.toLocaleString()}
                    </span>
                  )}
                </div>
              )}

              {/* No Diary Yet */}
              {!diary && (
                <div className="diary-create-section">
                  <h3>{t('journal.trade_diary.no_diary_title')}</h3>
                  <p>{t('journal.trade_diary.create_diary_hint')}</p>
                  <button className="btn-primary" onClick={handleCreateDiary}>
                    <Plus size={16} /> {t('journal.trade_diary.create_diary_btn')}
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
                        <h4>{t('journal.trade_diary.pillar_1_title')}</h4>
                      </div>
                      {expandedSection === 'pillar1' ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>
                    {expandedSection === 'pillar1' && (
                      <div className="pillar-body">
                        <div className="form-group">
                          <label>{t('journal.trade_diary.reasons_for_trade_label')}</label>
                          <textarea
                            value={diaryForm.reasons_for_trade}
                            onChange={e => setDiaryForm({ ...diaryForm, reasons_for_trade: e.target.value })}
                            rows={4}
                            placeholder={t('journal.trade_diary.reasons_placeholder')}
                          />
                        </div>
                        <div className="form-row">
                          <div className="form-group">
                            <label>{t('journal.trade_diary.chart_pattern_label')}</label>
                            <select
                              value={diaryForm.chart_pattern}
                              onChange={e => setDiaryForm({ ...diaryForm, chart_pattern: e.target.value })}
                            >
                              <option value="">{t('journal.common.select_option')}</option>
                              {CHART_PATTERNS.map(p => (
                                <option key={p.value} value={p.value}>{p.labelKey ? t(p.labelKey) : p.label}</option>
                              ))}
                            </select>
                          </div>
                          <div className="form-group">
                            <label>{t('journal.trade_diary.emotional_state_entry_label')}</label>
                            <select
                              value={diaryForm.emotional_state_entry}
                              onChange={e => setDiaryForm({ ...diaryForm, emotional_state_entry: e.target.value })}
                            >
                              <option value="">{t('journal.common.select_option')}</option>
                              {EMOTIONAL_STATES.map(s => (
                                <option key={s.value} value={s.value}>{s.emoji} {t(s.labelKey)}</option>
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
                        <h4>{t('journal.trade_diary.pillar_2_title')}</h4>
                        {isTradeOpen && <Lock size={14} className="pillar-lock" />}
                      </div>
                      {expandedSection === 'pillar2' ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>
                    {expandedSection === 'pillar2' && (
                      <div className="pillar-body">
                        {isTradeOpen && (
                          <div className="pillar-lock-notice">
                            <Lock size={14} />
                            <span>{t('journal.trade_diary.pillar_locked_hint')}</span>
                          </div>
                        )}
                        <div className="form-group">
                          <label>{t('journal.trade_diary.how_it_turned_out_label')}</label>
                          <textarea
                            value={diaryForm.how_it_turned_out}
                            onChange={e => setDiaryForm({ ...diaryForm, how_it_turned_out: e.target.value })}
                            rows={4}
                            placeholder={t('journal.trade_diary.how_it_turned_out_placeholder')}
                            disabled={isTradeOpen}
                          />
                        </div>
                        <div className="form-group">
                          <label>{t('journal.trade_diary.emotional_state_during_label')}</label>
                          <select
                            value={diaryForm.emotional_state_during}
                            onChange={e => setDiaryForm({ ...diaryForm, emotional_state_during: e.target.value })}
                            disabled={isTradeOpen}
                          >
                            <option value="">{t('journal.common.select_option')}</option>
                            {EMOTIONAL_STATES.map(s => (
                              <option key={s.value} value={s.value}>{s.emoji} {t(s.labelKey)}</option>
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
                        <h4>{t('journal.trade_diary.pillar_3_title')}</h4>
                        {isTradeOpen && <Lock size={14} className="pillar-lock" />}
                      </div>
                      {expandedSection === 'pillar3' ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>
                    {expandedSection === 'pillar3' && (
                      <div className="pillar-body">
                        {isTradeOpen && (
                          <div className="pillar-lock-notice">
                            <Lock size={14} />
                            <span>{t('journal.trade_diary.pillar_locked_hint')}</span>
                          </div>
                        )}
                        <div className="form-group">
                          <label>{t('journal.trade_diary.lessons_and_mistakes_label')}</label>
                          <textarea
                            value={diaryForm.lessons_and_mistakes}
                            onChange={e => setDiaryForm({ ...diaryForm, lessons_and_mistakes: e.target.value })}
                            rows={4}
                            placeholder={t('journal.trade_diary.lessons_placeholder')}
                            disabled={isTradeOpen}
                          />
                        </div>
                        <div className="form-group">
                          <label>{t('journal.trade_diary.emotional_state_exit_label')}</label>
                          <select
                            value={diaryForm.emotional_state_exit}
                            onChange={e => setDiaryForm({ ...diaryForm, emotional_state_exit: e.target.value })}
                            disabled={isTradeOpen}
                          >
                            <option value="">{t('journal.common.select_option')}</option>
                            {EMOTIONAL_STATES.map(s => (
                              <option key={s.value} value={s.value}>{s.emoji} {t(s.labelKey)}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Save Button */}
                  <div className="diary-save-bar">
                    <button className="btn-primary" onClick={handleSaveDiary}>
                      <Save size={16} /> {t('journal.trade_diary.save_diary_btn')}
                    </button>
                    {diary.diary_complete && (
                      <span className="diary-complete-badge">
                        <CheckCircle size={14} /> {t('journal.trade_diary.diary_complete_badge')}
                      </span>
                    )}
                  </div>

                  {/* Chart Upload Section */}
                  <div className="diary-pillar expanded">
                    <div className="pillar-header" style={{ cursor: 'default' }}>
                      <div className="pillar-header-left">
                        <Image size={18} className="pillar-icon pillar-icon-chart" />
                        <h4>{t('journal.trade_diary.charts_section')}</h4>
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
                            <label>{t('journal.trade_diary.select_image_label')}</label>
                            <input
                              type="file"
                              accept="image/*"
                              onChange={e => setUploadFile(e.target.files[0] || null)}
                              className="diary-file-input"
                            />
                          </div>
                          <div className="form-group">
                            <label>{t('journal.trade_diary.chart_type_label')}</label>
                            <select
                              value={uploadChartType}
                              onChange={e => setUploadChartType(e.target.value)}
                            >
                              <option value="">{t('journal.common.select_option')}</option>
                              {CHART_TYPES.map(ct => (
                                <option key={ct.value} value={ct.value}>{t(ct.labelKey)}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                        <div className="form-row">
                          <div className="form-group flex-2">
                            <label>{t('journal.trade_diary.chart_caption_label')}</label>
                            <input
                              type="text"
                              value={uploadCaption}
                              onChange={e => setUploadCaption(e.target.value)}
                              placeholder={t('journal.trade_diary.chart_caption_placeholder')}
                            />
                          </div>
                          <div className="form-actions-inline">
                            <button
                              className="btn-primary btn-sm"
                              onClick={handleUploadChart}
                              disabled={!uploadFile || uploading}
                            >
                              <Upload size={14} /> {uploading ? t('journal.trade_diary.uploading_chart') : t('journal.trade_diary.upload_chart_btn')}
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
          title={t('journal.trade_diary.delete_chart_confirm_title')}
          message={t('journal.trade_diary.delete_chart_confirm_msg')}
          onConfirm={handleDeleteChart}
          onCancel={() => setConfirmDeleteChart(null)}
          confirmText={t('journal.trade_diary.delete_chart_btn')}
          cancelText={t('journal.trade_diary.cancel_delete_chart_btn')}
          variant="danger"
        />
      )}
    </div>
  );
};

export default TradeDiary;
