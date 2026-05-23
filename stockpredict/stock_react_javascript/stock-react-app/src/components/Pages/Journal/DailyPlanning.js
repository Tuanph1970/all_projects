import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  CalendarDays, Plus, Save, Trash2, ChevronLeft, ChevronRight,
  Eye, TrendingUp, Lightbulb, Heart, RefreshCw,
  CheckCircle, Edit3, Repeat
} from 'lucide-react';
import journalService from '../../../services/journalService';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import '../../../styles/journal.css';

const DailyPlanning = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [lastReview, setLastReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [saveIsError, setSaveIsError] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [isEditing, setIsEditing] = useState(false);

  // Form fields
  const [form, setForm] = useState({
    market_review: '',
    new_trade_ideas: '',
    stop_objective_updates: '',
    emotional_checkin: '',
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

  // Load plans when account changes
  const loadPlans = useCallback(async () => {
    if (!selectedAccountId) return;
    try {
      const res = await journalService.getDailyPlans(selectedAccountId);
      setPlans(res.data || res || []);
    } catch { setPlans([]); }
  }, [selectedAccountId]);

  useEffect(() => { loadPlans(); }, [loadPlans]);

  // Load latest weekly review for carry-forward of key_adjustments.
  // Repository orders by week_start desc, so limit=1 gives the most recent.
  useEffect(() => {
    if (!selectedAccountId) {
      setLastReview(null);
      return;
    }
    (async () => {
      try {
        const res = await journalService.getWeeklyReviews(selectedAccountId, 1, 0);
        const data = res.data || res || [];
        const list = Array.isArray(data) ? data : (data.items || []);
        setLastReview(list[0] || null);
      } catch {
        setLastReview(null);
      }
    })();
  }, [selectedAccountId]);

  const lastWeekBullets = useMemo(() => {
    if (!lastReview?.key_adjustments) return [];
    return lastReview.key_adjustments
      .split('\n')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  }, [lastReview]);

  // Load or create plan for selected date
  const loadPlanForDate = useCallback(async () => {
    if (!selectedAccountId || !selectedDate) return;
    // Check if plan exists in loaded plans
    const existing = plans.find(p => p.plan_date === selectedDate);
    if (existing) {
      setSelectedPlan(existing);
      setForm({
        market_review: existing.market_review || '',
        new_trade_ideas: existing.new_trade_ideas || '',
        stop_objective_updates: existing.stop_objective_updates || '',
        emotional_checkin: existing.emotional_checkin || '',
      });
      setIsEditing(false);
    } else {
      setSelectedPlan(null);
      setForm({ market_review: '', new_trade_ideas: '', stop_objective_updates: '', emotional_checkin: '' });
      setIsEditing(true);
    }
  }, [selectedDate, plans, selectedAccountId]);

  useEffect(() => { loadPlanForDate(); }, [loadPlanForDate]);

  const handleSave = async () => {
    if (!selectedAccountId) return;
    setSaving(true);
    setSaveMsg('');
    setSaveIsError(false);
    try {
      if (selectedPlan) {
        // Update existing
        const res = await journalService.updateDailyPlan(selectedAccountId, selectedPlan.id, form);
        const updated = res.data || res;
        setSelectedPlan(updated);
        setSaveMsg(t('journal.daily_planning.save_success'));
      } else {
        // Create new
        const res = await journalService.createDailyPlan(selectedAccountId, {
          plan_date: selectedDate,
          ...form,
        });
        const created = res.data || res;
        setSelectedPlan(created);
        setSaveMsg(t('journal.daily_planning.plan_created'));
        await loadPlans();
      }
      setIsEditing(false);
    } catch {
      setSaveMsg(t('journal.daily_planning.save_error'));
      setSaveIsError(true);
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(''), 3000);
    }
  };

  const handleDelete = async () => {
    if (!selectedPlan || !window.confirm(t('journal.daily_planning.delete_plan_confirm'))) return;
    try {
      await journalService.deleteDailyPlan(selectedAccountId, selectedPlan.id);
      setSelectedPlan(null);
      setForm({ market_review: '', new_trade_ideas: '', stop_objective_updates: '', emotional_checkin: '' });
      setIsEditing(true);
      await loadPlans();
    } catch { /* ignore */ }
  };

  const navigateDate = (days) => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + days);
    setSelectedDate(d.toISOString().split('T')[0]);
  };

  const isComplete = form.market_review && form.new_trade_ideas && form.stop_objective_updates && form.emotional_checkin;

  if (loading) {
    return (
      <div className="journal-accounts">
        <div className="journal-empty">
          <RefreshCw size={40} className="spin" />
          <p>{t('journal.common.loading')}</p>
        </div>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="journal-accounts">
        <div className="journal-empty">
          <CalendarDays size={48} />
          <h3>{t('journal.common.no_accounts_title')}</h3>
          <p>{t('journal.daily_planning.create_account_first_hint')}</p>
          <button className="btn-primary" onClick={() => navigate('/journal-accounts')} style={{ marginTop: '12px' }}>
            <Plus size={16} /> {t('journal.common.create_account_btn')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="jplan">
      {/* Header */}
      <div className="jplan-header">
        <div className="jplan-title">
          <CalendarDays size={22} />
          <h2>{t('journal.daily_planning.title')}</h2>
        </div>
        <select
          value={selectedAccountId || ''}
          onChange={(e) => setSelectedAccountId(Number(e.target.value))}
          className="jdash-account-select"
        >
          {accounts.map(a => (
            <option key={a.id} value={a.id}>{a.account_name}</option>
          ))}
        </select>
      </div>

      {/* Schwager quote */}
      <div className="jplan-quote">
        <em>{t('journal.daily_planning.schwager_quote')}</em>
        <span>{t('journal.daily_planning.schwager_attribution')}</span>
      </div>

      {lastWeekBullets.length > 0 && (
        <div className="jplan-last-adjustments" data-testid="last-adjustments">
          <div className="jplan-last-adjustments-header">
            <Repeat size={16} />
            <h4>{t('journal.daily_planning.last_adjustments_title')}</h4>
            {lastReview?.week_start && (
              <span className="jplan-last-adjustments-week">
                {t('journal.daily_planning.week_label', { date: formatDateVN(lastReview.week_start) })}
              </span>
            )}
          </div>
          <ul>
            {lastWeekBullets.map((b, i) => <li key={i}>{b}</li>)}
          </ul>
        </div>
      )}

      <div className="jplan-layout">
        {/* Left: Plan History */}
        <div className="jplan-sidebar">
          <h4>{t('journal.daily_planning.plan_history_title')}</h4>
          <div className="jplan-plan-list">
            {plans.length === 0 ? (
              <p className="jplan-no-plans">{t('journal.daily_planning.no_plans_message')}</p>
            ) : (
              plans.map(p => (
                <div
                  key={p.id}
                  className={`jplan-plan-item ${selectedPlan?.id === p.id ? 'active' : ''}`}
                  onClick={() => setSelectedDate(p.plan_date)}
                >
                  <CalendarDays size={14} />
                  <span>{formatDateVN(p.plan_date)}</span>
                  {p.market_review && p.new_trade_ideas && p.stop_objective_updates && p.emotional_checkin ? (
                    <CheckCircle size={14} className="jplan-complete-icon" />
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Plan Editor */}
        <div className="jplan-editor">
          {/* Date navigator */}
          <div className="jplan-date-nav">
            <button className="btn-icon" onClick={() => navigateDate(-1)}>
              <ChevronLeft size={18} />
            </button>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="jplan-date-input"
            />
            <button className="btn-icon" onClick={() => navigateDate(1)}>
              <ChevronRight size={18} />
            </button>
            <button
              className="btn-secondary btn-sm"
              onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}
            >
              {t('journal.daily_planning.today_btn')}
            </button>

            <div className="jplan-date-actions">
              {selectedPlan && !isEditing && (
                <button className="btn-icon" onClick={() => setIsEditing(true)} title={t('journal.daily_planning.edit_tooltip')}>
                  <Edit3 size={16} />
                </button>
              )}
              {selectedPlan && (
                <button className="btn-icon btn-danger" onClick={handleDelete} title={t('journal.daily_planning.delete_tooltip')}>
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          </div>

          {isComplete && (
            <div className="jplan-complete-badge">
              <CheckCircle size={14} /> {t('journal.daily_planning.plan_complete_badge')}
            </div>
          )}

          {/* Four Schwager sections */}
          <div className="jplan-sections">
            <PlanSection
              icon={<Eye size={18} />}
              title={t('journal.daily_planning.section_1_title')}
              subtitle={t('journal.daily_planning.section_1_subtitle')}
              value={form.market_review}
              onChange={(v) => setForm(prev => ({ ...prev, market_review: v }))}
              disabled={!isEditing}
              color="#3b82f6"
            />
            <PlanSection
              icon={<Lightbulb size={18} />}
              title={t('journal.daily_planning.section_2_title')}
              subtitle={t('journal.daily_planning.section_2_subtitle')}
              value={form.new_trade_ideas}
              onChange={(v) => setForm(prev => ({ ...prev, new_trade_ideas: v }))}
              disabled={!isEditing}
              color="#f59e0b"
            />
            <PlanSection
              icon={<TrendingUp size={18} />}
              title={t('journal.daily_planning.section_3_title')}
              subtitle={t('journal.daily_planning.section_3_subtitle')}
              value={form.stop_objective_updates}
              onChange={(v) => setForm(prev => ({ ...prev, stop_objective_updates: v }))}
              disabled={!isEditing}
              color="#10b981"
            />
            <PlanSection
              icon={<Heart size={18} />}
              title={t('journal.daily_planning.section_4_title')}
              subtitle={t('journal.daily_planning.section_4_subtitle')}
              value={form.emotional_checkin}
              onChange={(v) => setForm(prev => ({ ...prev, emotional_checkin: v }))}
              disabled={!isEditing}
              color="#ec4899"
            />
          </div>

          {/* Save button */}
          {isEditing && (
            <div className="jplan-save-bar">
              <button className="btn-primary" onClick={handleSave} disabled={saving}>
                <Save size={16} />
                {saving ? t('journal.common.saving') : (selectedPlan ? t('journal.daily_planning.update_btn') : t('journal.daily_planning.create_btn'))}
              </button>
              {selectedPlan && (
                <button className="btn-secondary" onClick={() => {
                  loadPlanForDate();
                  setIsEditing(false);
                }}>
                  {t('journal.common.cancel_btn')}
                </button>
              )}
              {saveMsg && (
                <span className={`jplan-save-msg ${saveIsError ? 'error' : 'success'}`}>
                  {saveMsg}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Sub-components

const PlanSection = ({ icon, title, subtitle, value, onChange, disabled, color }) => {
  const { t } = useTranslation();
  return (
    <div className="jplan-section">
      <div className="jplan-section-header" style={{ borderLeftColor: color }}>
        <span style={{ color }}>{icon}</span>
        <div>
          <h4>{title}</h4>
          <p>{subtitle}</p>
        </div>
      </div>
      <textarea
        className="jplan-textarea"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={disabled ? t('journal.common.placeholder_no_content') : t('journal.common.placeholder_enter_content')}
        rows={4}
      />
    </div>
  );
};

const formatDateVN = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' });
};

export default DailyPlanning;
