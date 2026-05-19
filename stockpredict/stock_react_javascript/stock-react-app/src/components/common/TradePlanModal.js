// F-033 / F-090..F-093 — TradePlanModal (Phase J: journal auto-integration)
//
// Phase J changes:
//  F-090  Fixed field mapping to match journal-service TradeCreate schema
//  F-091  Auto-creates diary entry with recommendation context after save
//  F-092  Inline success confirmation (trade-log + diary navigation links)
//  F-093  Removed alert() from onSaved callsite in DecisionConsole
import React, { useState, useEffect } from 'react';
import { X, AlertTriangle, CheckCircle, Target, Shield, BookOpen, List } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import journalService from '../../services/journalService';

const ACTION_COLORS = {
  BUY: '#10b981',
  SELL: '#ef4444',
  SELL_SHORT: '#f59e0b',
  COVER: '#3b82f6',
  HOLD: '#6b7280',
  WAIT: '#6b7280',
  REVERSE: '#8b5cf6',
};

// Build pre_trade_analysis text from recommendation context
const buildReasonsText = (rec) => {
  const parts = [];
  if (rec.signal_kind) {
    const conf = rec.confidence != null ? ` — ${(rec.confidence * 100).toFixed(0)}% confidence` : '';
    const confirmed = rec.signal_confirmed ? ' (confirmed)' : ' (unconfirmed)';
    parts.push(`Signal: ${rec.signal_kind}${confirmed}${conf}`);
  }
  if (rec.regime) parts.push(`Regime: ${rec.regime}`);
  if (rec.reason_chain?.length) {
    parts.push('Reason chain:');
    rec.reason_chain.slice(0, 4).forEach(s => parts.push(`  • [${s.stage}] ${s.message}`));
  }
  if (rec.discipline_violations?.length) {
    const msgs = rec.discipline_violations.map(v => `[${v.rule_id}] ${v.message}`).join('; ');
    parts.push(`Discipline: ${msgs}`);
  }
  parts.push(`Source: Decision Helper — ${rec.bar_date}`);
  return parts.join('\n');
};

// ── Success view shown after saving ──────────────────────────────────────────

const SuccessView = ({ tradeId, onNavigate, onClose }) => (
  <div style={styles.successBox}>
    <CheckCircle size={36} color="#10b981" style={{ marginBottom: 12 }} />
    <div style={{ fontSize: 16, fontWeight: 700, color: '#f9fafb', marginBottom: 4 }}>
      Trade plan saved
    </div>
    <div style={{ fontSize: 13, color: '#9ca3af', marginBottom: 20 }}>
      Trade #{tradeId} created with pre-filled diary entry.
    </div>
    <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
      <button
        onClick={() => onNavigate('/trade-log')}
        style={{ ...styles.navBtn, background: '#374151' }}
      >
        <List size={14} /> Trade Log
      </button>
      <button
        onClick={() => onNavigate('/trade-diary')}
        style={{ ...styles.navBtn, background: '#3b82f6' }}
      >
        <BookOpen size={14} /> Open Diary
      </button>
      <button onClick={onClose} style={{ ...styles.navBtn, background: 'transparent', border: '1px solid #374151', color: '#6b7280' }}>
        Close
      </button>
    </div>
  </div>
);

// ── Main modal ────────────────────────────────────────────────────────────────

const TradePlanModal = ({ isOpen, onClose, recommendation, onSaved }) => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    entry_price: '',
    stop_price: '',
    target_price: '',
    shares: '',
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [saved, setSaved] = useState(null);   // {tradeId} on success

  // Pre-fill from recommendation whenever it changes
  useEffect(() => {
    if (!recommendation) return;
    setSaved(null);
    setError(null);
    setForm({
      entry_price: recommendation.entry_price ?? '',
      stop_price: recommendation.stop_price ?? '',
      target_price: recommendation.target_price ?? '',
      shares: recommendation.position_size ?? '',
      notes: '',
    });
  }, [recommendation]);

  // Load journal accounts for selector
  useEffect(() => {
    if (!isOpen) return;
    journalService.getAccounts()
      .then(data => {
        const list = Array.isArray(data) ? data : (data.accounts || []);
        setAccounts(list);
        if (list.length > 0) setSelectedAccount(String(list[0].id));
      })
      .catch(() => setAccounts([]));
  }, [isOpen]);

  if (!isOpen || !recommendation) return null;

  const stopMissing = !form.stop_price || Number(form.stop_price) <= 0;
  const targetMissing = !form.target_price || Number(form.target_price) <= 0;
  const canSave = !stopMissing && !targetMissing && selectedAccount;
  const isEntry = ['BUY', 'SELL_SHORT'].includes(recommendation.action);

  const handleChange = (field) => (e) => setForm(prev => ({ ...prev, [field]: e.target.value }));

  const handleSave = async () => {
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      // F-090: correct field names matching journal-service TradeCreate schema
      const direction = recommendation.action === 'BUY' ? 'Long' : 'Short';
      const tradeResult = await journalService.createTrade(selectedAccount, {
        market_ticker: recommendation.ticker,
        direction,
        entry_date: recommendation.bar_date,
        entry_price: Number(form.entry_price),
        entry_type: 'Market',
        initial_stop: Number(form.stop_price),
        position_size: Number(form.shares) || 1,
        objective_1: Number(form.target_price),
        commission: 0,
        entry_reason: form.notes ||
          `${recommendation.signal_kind || 'Signal'} · ${recommendation.regime} · Decision Helper`,
      });

      const tradeId = tradeResult?.id;

      // F-091: auto-create diary entry with recommendation context (best-effort)
      if (tradeId) {
        try {
          await journalService.createOrGetDiary(tradeId, {
            reasons_for_trade: buildReasonsText(recommendation),
          });
        } catch { /* diary is optional — don't fail the whole save */ }
      }

      // F-092: inline success instead of alert()
      setSaved({ tradeId });
      onSaved && onSaved(tradeId);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save trade plan');
    } finally {
      setSaving(false);
    }
  };

  const handleNavigate = (path) => {
    onClose();
    navigate(path);
  };

  const actionColor = ACTION_COLORS[recommendation.action] || '#6b7280';
  const riskReward = (form.stop_price && form.target_price && form.entry_price)
    ? Math.abs(Number(form.target_price) - Number(form.entry_price)) /
      Math.abs(Number(form.entry_price) - Number(form.stop_price))
    : null;

  return (
    <div style={styles.overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ ...styles.actionBadge, background: actionColor }}>
              {recommendation.action}
            </span>
            <span style={styles.ticker}>{recommendation.ticker}</span>
            <span style={styles.barDate}>{recommendation.bar_date}</span>
          </div>
          <button onClick={onClose} style={styles.closeBtn}><X size={18} /></button>
        </div>

        {/* Success view replaces the form */}
        {saved ? (
          <SuccessView
            tradeId={saved.tradeId}
            onNavigate={handleNavigate}
            onClose={onClose}
          />
        ) : (
          <>
            {/* Discipline gate warning */}
            {(stopMissing || targetMissing) && (
              <div style={styles.gateWarning}>
                <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                <span>
                  {stopMissing && targetMissing
                    ? 'Stop-loss and target are required before saving this plan (Ch 17).'
                    : stopMissing
                      ? 'Stop-loss is required — you must know your exit before entering.'
                      : 'Profit target is required — define your objective before entering.'}
                </span>
              </div>
            )}

            {/* Body */}
            <div style={styles.body}>
              {/* Account selector */}
              <div style={styles.field}>
                <label style={styles.label}>Journal Account</label>
                <select
                  value={selectedAccount}
                  onChange={e => setSelectedAccount(e.target.value)}
                  style={styles.input}
                >
                  {accounts.length === 0
                    ? <option value="">No accounts found</option>
                    : accounts.map(a => (
                        <option key={a.id} value={String(a.id)}>
                          {a.account_name || `Account ${a.id}`}
                        </option>
                      ))}
                </select>
              </div>

              {/* Price fields */}
              <div style={styles.row}>
                <div style={styles.field}>
                  <label style={styles.label}>Entry Price</label>
                  <input
                    type="number" step="0.01" value={form.entry_price}
                    onChange={handleChange('entry_price')} style={styles.input}
                  />
                </div>
                <div style={styles.field}>
                  <label style={{ ...styles.label, color: stopMissing ? '#ef4444' : '#d1d5db' }}>
                    <Shield size={13} style={{ marginRight: 4 }} /> Stop-Loss *
                  </label>
                  <input
                    type="number" step="0.01" value={form.stop_price}
                    onChange={handleChange('stop_price')}
                    style={{ ...styles.input, borderColor: stopMissing ? '#ef4444' : '#374151' }}
                  />
                </div>
                <div style={styles.field}>
                  <label style={{ ...styles.label, color: targetMissing ? '#ef4444' : '#d1d5db' }}>
                    <Target size={13} style={{ marginRight: 4 }} /> Target *
                  </label>
                  <input
                    type="number" step="0.01" value={form.target_price}
                    onChange={handleChange('target_price')}
                    style={{ ...styles.input, borderColor: targetMissing ? '#ef4444' : '#374151' }}
                  />
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>Shares</label>
                  <input
                    type="number" value={form.shares}
                    onChange={handleChange('shares')} style={styles.input}
                  />
                </div>
              </div>

              {/* R:R display */}
              {riskReward !== null && (
                <div style={styles.rrRow}>
                  <CheckCircle size={14} color={riskReward >= 1.5 ? '#10b981' : '#f59e0b'} />
                  <span style={{ color: riskReward >= 1.5 ? '#10b981' : '#f59e0b', fontSize: 13 }}>
                    R:R = {riskReward.toFixed(2)}:1
                    {riskReward < 1 && '  — below 1:1, reconsider'}
                  </span>
                </div>
              )}

              {/* Notes */}
              <div style={styles.field}>
                <label style={styles.label}>Notes / Setup reason</label>
                <textarea
                  value={form.notes}
                  onChange={handleChange('notes')}
                  rows={3}
                  placeholder={`${recommendation.signal_kind || 'Signal'} on ${recommendation.regime}`}
                  style={{ ...styles.input, resize: 'vertical' }}
                />
              </div>

              {/* Diary preview */}
              <div style={styles.diaryPreview}>
                <BookOpen size={12} color="#a78bfa" style={{ flexShrink: 0, marginTop: 1 }} />
                <span style={{ color: '#9ca3af', fontSize: 11 }}>
                  A diary entry will be auto-created with signal context and reason chain.
                </span>
              </div>
            </div>

            {/* Footer */}
            {error && <div style={styles.errorMsg}>{error}</div>}
            <div style={styles.footer}>
              <button onClick={onClose} style={styles.cancelBtn}>Cancel</button>
              <button
                onClick={handleSave}
                disabled={!canSave || saving || !isEntry}
                style={{
                  ...styles.saveBtn,
                  opacity: (!canSave || saving || !isEntry) ? 0.4 : 1,
                  cursor: (!canSave || saving || !isEntry) ? 'not-allowed' : 'pointer',
                }}
              >
                {saving ? 'Saving…' : 'Save Trade Plan'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const styles = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
  },
  modal: {
    background: '#1f2937', borderRadius: 12, width: '100%', maxWidth: 560,
    boxShadow: '0 25px 50px rgba(0,0,0,0.5)', display: 'flex', flexDirection: 'column',
  },
  header: {
    padding: '16px 20px', borderBottom: '1px solid #374151',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  actionBadge: {
    padding: '3px 10px', borderRadius: 6, color: '#fff', fontSize: 12, fontWeight: 700, letterSpacing: 1,
  },
  ticker: { fontSize: 18, fontWeight: 700, color: '#f9fafb' },
  barDate: { fontSize: 12, color: '#9ca3af', marginLeft: 4 },
  closeBtn: { background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', padding: 4 },
  gateWarning: {
    margin: '12px 20px 0',
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 8, padding: '10px 14px',
    display: 'flex', gap: 8, alignItems: 'flex-start', color: '#fca5a5', fontSize: 13,
  },
  body: { padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 12 },
  row: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 10 },
  field: { display: 'flex', flexDirection: 'column', gap: 4 },
  label: {
    fontSize: 11, fontWeight: 600, color: '#d1d5db',
    textTransform: 'uppercase', letterSpacing: 0.5, display: 'flex', alignItems: 'center',
  },
  input: {
    background: '#111827', border: '1px solid #374151', borderRadius: 6,
    padding: '7px 10px', color: '#f9fafb', fontSize: 13, width: '100%', outline: 'none',
  },
  rrRow: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '6px 10px', background: '#111827', borderRadius: 6,
  },
  diaryPreview: {
    display: 'flex', gap: 7, alignItems: 'flex-start',
    padding: '7px 10px', background: 'rgba(167,139,250,0.08)',
    border: '1px solid rgba(167,139,250,0.2)', borderRadius: 6,
  },
  errorMsg: {
    margin: '0 20px 8px', padding: '8px 12px',
    background: 'rgba(239,68,68,0.1)', borderRadius: 6, color: '#fca5a5', fontSize: 13,
  },
  footer: {
    padding: '14px 20px', borderTop: '1px solid #374151',
    display: 'flex', justifyContent: 'flex-end', gap: 10,
  },
  cancelBtn: {
    padding: '8px 18px', borderRadius: 7, background: '#374151',
    border: 'none', color: '#d1d5db', cursor: 'pointer', fontSize: 14,
  },
  saveBtn: {
    padding: '8px 20px', borderRadius: 7, background: '#3b82f6',
    border: 'none', color: '#fff', fontWeight: 600, fontSize: 14,
  },
  // Success view
  successBox: {
    padding: '32px 24px', display: 'flex', flexDirection: 'column',
    alignItems: 'center', textAlign: 'center',
  },
  navBtn: {
    padding: '8px 18px', borderRadius: 7, border: 'none',
    color: '#fff', fontWeight: 600, fontSize: 13, cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 6,
  },
};

export default TradePlanModal;
