// Risk preferences inline panel — shown when user clicks the settings icon
import React, { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import helperService from '../../../services/helperService';

const RiskPrefsPanel = ({ onClose }) => {
  const [form, setForm] = useState({
    accountEquity: 100000,
    riskPerTradePct: 1.0,
    maxConcurrentPositions: 5,
    maxCorrelation: 0.7,
    lossStreakSizeCut: 0.5,
    lossStreakThreshold: 3,
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
      }))
      .catch(() => {});
  }, []);

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: Number(e.target.value) }));

  const save = async () => {
    setSaving(true);
    setMsg('');
    try {
      await helperService.saveRiskPrefs(form);
      setMsg('Saved.');
      setTimeout(() => setMsg(''), 2000);
    } catch {
      setMsg('Save failed.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={{ fontWeight: 700, fontSize: 14 }}>Risk Preferences</span>
        <button onClick={onClose} style={styles.closeBtn}><X size={14} /></button>
      </div>
      <div style={styles.grid}>
        <Field label="Account Equity" value={form.accountEquity} onChange={set('accountEquity')} step={1000} />
        <Field label="Risk / Trade %" value={form.riskPerTradePct} onChange={set('riskPerTradePct')} step={0.1} min={0.1} max={10} />
        <Field label="Max Positions" value={form.maxConcurrentPositions} onChange={set('maxConcurrentPositions')} step={1} min={1} max={20} />
        <Field label="Max Correlation" value={form.maxCorrelation} onChange={set('maxCorrelation')} step={0.05} min={0} max={1} />
        <Field label="Streak Cut Factor" value={form.lossStreakSizeCut} onChange={set('lossStreakSizeCut')} step={0.1} min={0} max={1} />
        <Field label="Streak Threshold" value={form.lossStreakThreshold} onChange={set('lossStreakThreshold')} step={1} min={1} max={10} />
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10 }}>
        <button onClick={save} disabled={saving} style={styles.saveBtn}>
          <Save size={13} />{saving ? 'Saving…' : 'Save'}
        </button>
        {msg && <span style={{ fontSize: 12, color: '#10b981' }}>{msg}</span>}
      </div>
    </div>
  );
};

const Field = ({ label, value, onChange, step, min, max }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
    <label style={{ fontSize: 10, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</label>
    <input
      type="number" value={value} onChange={onChange} step={step} min={min} max={max}
      style={{ background: '#111827', border: '1px solid #374151', borderRadius: 5, padding: '5px 8px', color: '#f9fafb', fontSize: 13, outline: 'none' }}
    />
  </div>
);

const styles = {
  panel: {
    background: '#1f2937', border: '1px solid #374151', borderRadius: 10,
    padding: 16, marginBottom: 14,
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12,
  },
  closeBtn: { background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 },
  saveBtn: {
    background: '#3b82f6', border: 'none', borderRadius: 6,
    padding: '7px 14px', color: '#fff', fontWeight: 600, fontSize: 13,
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
  },
};

export default RiskPrefsPanel;
