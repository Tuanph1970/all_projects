// Risk preferences inline panel — shown when user clicks the settings icon
import React, { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import helperService from '../../../services/helperService';

const RiskPrefsPanel = ({ onClose }) => {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    accountEquity: 100000,
    riskPerTradePct: 1.0,
    maxConcurrentPositions: 5,
    maxCorrelation: 0.7,
    lossStreakSizeCut: 0.5,
    lossStreakThreshold: 3,
    journalAccountId: '',
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    helperService.getRiskPrefs()
      .then(d => setForm({
        accountEquity: d.account_equity,
        riskPerTradePct: d.risk_per_trade_pct,
        maxConcurrentPositions: d.max_concurrent_positions,
        maxCorrelation: d.max_correlation,
        lossStreakSizeCut: d.loss_streak_size_cut,
        lossStreakThreshold: d.loss_streak_threshold,
        journalAccountId: d.journal_account_id ?? '',
      }))
      .catch(() => {});
  }, []);

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: Number(e.target.value) }));
  const setStr = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  const save = async () => {
    setSaving(true);
    setMsg('');
    try {
      await helperService.saveRiskPrefs({
        ...form,
        journalAccountId: form.journalAccountId ? Number(form.journalAccountId) : null,
      });
      setMsg(t('decision_helper.risk_prefs.saved'));
      setTimeout(() => setMsg(''), 2000);
    } catch {
      setMsg(t('decision_helper.risk_prefs.save_failed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={{ fontWeight: 700, fontSize: 14 }}>{t('decision_helper.risk_prefs.title')}</span>
        <button onClick={onClose} style={styles.closeBtn}><X size={14} /></button>
      </div>
      <div className="responsive-stack" style={styles.grid}>
        <Field label={t('decision_helper.risk_prefs.account_equity')} value={form.accountEquity} onChange={set('accountEquity')} step={1000} />
        <Field label={t('decision_helper.risk_prefs.risk_per_trade')} value={form.riskPerTradePct} onChange={set('riskPerTradePct')} step={0.1} min={0.1} max={10} />
        <Field label={t('decision_helper.risk_prefs.max_positions')} value={form.maxConcurrentPositions} onChange={set('maxConcurrentPositions')} step={1} min={1} max={20} />
        <Field label={t('decision_helper.risk_prefs.max_correlation')} value={form.maxCorrelation} onChange={set('maxCorrelation')} step={0.05} min={0} max={1} />
        <Field label={t('decision_helper.risk_prefs.streak_cut')} value={form.lossStreakSizeCut} onChange={set('lossStreakSizeCut')} step={0.1} min={0} max={1} />
        <Field label={t('decision_helper.risk_prefs.streak_threshold')} value={form.lossStreakThreshold} onChange={set('lossStreakThreshold')} step={1} min={1} max={10} />
      </div>
      <div style={{ marginTop: 10 }}>
        <label style={{ fontSize: 10, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          {t('decision_helper.risk_prefs.journal_account')}
        </label>
        <input
          type="number" value={form.journalAccountId} onChange={setStr('journalAccountId')}
          placeholder={t('decision_helper.risk_prefs.journal_placeholder')}
          style={{ display: 'block', width: '100%', marginTop: 4, background: '#ffffff', border: '1px solid #d1d5db', borderRadius: 5, padding: '5px 8px', color: '#111827', fontSize: 13, outline: 'none' }}
        />
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10 }}>
        <button onClick={save} disabled={saving} style={styles.saveBtn}>
          <Save size={13} />{saving ? t('decision_helper.common.saving') : t('decision_helper.common.save')}
        </button>
        {msg && <span style={{ fontSize: 12, color: '#10b981' }}>{msg}</span>}
      </div>
    </div>
  );
};

const Field = ({ label, value, onChange, step, min, max }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
    <label style={{ fontSize: 10, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</label>
    <input
      type="number" value={value} onChange={onChange} step={step} min={min} max={max}
      style={{ background: '#ffffff', border: '1px solid #d1d5db', borderRadius: 5, padding: '5px 8px', color: '#111827', fontSize: 13, outline: 'none' }}
    />
  </div>
);

const styles = {
  panel: {
    background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 10,
    padding: 16, marginBottom: 14,
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12,
  },
  closeBtn: { background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 },
  saveBtn: {
    background: '#3b82f6', border: 'none', borderRadius: 6,
    padding: '7px 14px', color: '#fff', fontWeight: 600, fontSize: 13,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
  },
};

export default RiskPrefsPanel;
