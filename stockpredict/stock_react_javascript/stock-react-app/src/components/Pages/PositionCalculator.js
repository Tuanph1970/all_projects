import React, { useMemo, useState } from 'react';
import { Calculator, TrendingDown, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/**
 * Schwager-style position-size calculator.
 *
 * Given account equity, max risk %, entry, and stop, computes:
 *   - risk amount (VND): equity * max_risk_pct / 100
 *   - shares: floor(risk_amount / |entry - stop|)
 *   - position value: shares * entry
 *   - actual risk %: (shares * |entry - stop|) / equity * 100
 *
 * Pure UI component — no backend calls.
 */
const PositionCalculator = () => {
  const { t, i18n } = useTranslation();
  const [equity, setEquity] = useState(100_000_000);
  const [riskPct, setRiskPct] = useState(2);
  const [entry, setEntry] = useState(100);
  const [stop, setStop] = useState(95);
  const [direction, setDirection] = useState('long');

  const result = useMemo(() => {
    const e = Number(equity), r = Number(riskPct);
    const en = Number(entry), st = Number(stop);
    if (!e || !r || !en || !st) return null;

    // Validate stop placement against direction
    let directionWarning = null;
    if (direction === 'long' && st >= en) {
      directionWarning = t('tools.calculator.long_stop_warning');
    } else if (direction === 'short' && st <= en) {
      directionWarning = t('tools.calculator.short_stop_warning');
    }

    const perShareRisk = Math.abs(en - st);
    if (perShareRisk === 0) return null;

    const riskAmount = e * (r / 100);
    const shares = Math.floor(riskAmount / perShareRisk);
    const positionValue = shares * en;
    const actualRiskAmount = shares * perShareRisk;
    const actualRiskPct = (actualRiskAmount / e) * 100;
    const exposurePct = (positionValue / e) * 100;
    const r1Target = direction === 'long' ? en + perShareRisk : en - perShareRisk;
    const r2Target = direction === 'long' ? en + perShareRisk * 2 : en - perShareRisk * 2;
    const r3Target = direction === 'long' ? en + perShareRisk * 3 : en - perShareRisk * 3;

    return {
      riskAmount,
      shares,
      positionValue,
      actualRiskAmount,
      actualRiskPct,
      exposurePct,
      perShareRisk,
      r1Target,
      r2Target,
      r3Target,
      directionWarning,
    };
  }, [equity, riskPct, entry, stop, direction, t]);

  // VND is always VND, but switch the digit-grouping locale to match the
  // active language so "100,000" vs "100.000" feels right.
  const numLocale = i18n.language === 'en' ? 'en-US' : 'vi-VN';
  const fmtVND = (v) => new Intl.NumberFormat(numLocale, { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v);
  const fmtNum = (v) => new Intl.NumberFormat(numLocale).format(Math.round(v));

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <h1 style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <Calculator color="#6366f1" />
        {t('tools.calculator.title')}
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24 }}>
        {t('tools.calculator.subtitle')}
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Inputs */}
        <div style={{ background: '#fff', padding: 20, borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <h3 style={{ marginTop: 0, marginBottom: 16 }}>{t('tools.calculator.parameters_label')}</h3>

          <div style={{ marginBottom: 12 }}>
            <label htmlFor="pc-equity" style={{ display: 'block', fontSize: 13, color: '#4b5563', marginBottom: 4 }}>{t('tools.calculator.equity_label')}</label>
            <input
              id="pc-equity"
              type="number"
              value={equity}
              onChange={(e) => setEquity(e.target.value)}
              min={0}
              step={1_000_000}
              style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 6 }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label htmlFor="pc-risk-pct" style={{ display: 'block', fontSize: 13, color: '#4b5563', marginBottom: 4 }}>{t('tools.calculator.max_risk_label')}</label>
            <input
              id="pc-risk-pct"
              type="number"
              value={riskPct}
              onChange={(e) => setRiskPct(e.target.value)}
              min={0.1}
              max={10}
              step={0.1}
              style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 6 }}
            />
            <small style={{ color: '#6b7280' }}>{t('tools.calculator.risk_recommendation')}</small>
          </div>

          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <button
              type="button"
              onClick={() => setDirection('long')}
              style={{ flex: 1, padding: 8, border: '1px solid #d1d5db', borderRadius: 6,
                background: direction === 'long' ? '#10b981' : '#fff',
                color: direction === 'long' ? '#fff' : '#4b5563',
                cursor: 'pointer' }}
            >{t('tools.calculator.long_button')}</button>
            <button
              type="button"
              onClick={() => setDirection('short')}
              style={{ flex: 1, padding: 8, border: '1px solid #d1d5db', borderRadius: 6,
                background: direction === 'short' ? '#dc2626' : '#fff',
                color: direction === 'short' ? '#fff' : '#4b5563',
                cursor: 'pointer' }}
            >{t('tools.calculator.short_button')}</button>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label htmlFor="pc-entry" style={{ display: 'block', fontSize: 13, color: '#4b5563', marginBottom: 4 }}>{t('tools.calculator.entry_price_label')}</label>
            <input
              id="pc-entry"
              type="number"
              value={entry}
              onChange={(e) => setEntry(e.target.value)}
              min={0}
              step={0.01}
              style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 6 }}
            />
          </div>

          <div>
            <label htmlFor="pc-stop" style={{ display: 'block', fontSize: 13, color: '#4b5563', marginBottom: 4 }}>{t('tools.calculator.stop_loss_label')}</label>
            <input
              id="pc-stop"
              type="number"
              value={stop}
              onChange={(e) => setStop(e.target.value)}
              min={0}
              step={0.01}
              style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 6 }}
            />
          </div>
        </div>

        {/* Results */}
        <div style={{ background: '#fff', padding: 20, borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <h3 style={{ marginTop: 0, marginBottom: 16 }}>{t('tools.calculator.results_label')}</h3>

          {!result ? (
            <p style={{ color: '#6b7280' }}>{t('tools.calculator.enter_parameters_message')}</p>
          ) : (
            <>
              {result.directionWarning && (
                <div style={{ display: 'flex', gap: 8, padding: 10, background: '#fef3c7', color: '#92400e', borderRadius: 6, marginBottom: 12 }}>
                  <AlertTriangle size={16} />
                  <span style={{ fontSize: 13 }}>{result.directionWarning}</span>
                </div>
              )}

              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{t('tools.calculator.shares_label')}</div>
                <div data-testid="pc-shares" style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{fmtNum(result.shares)}</div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                <Cell label={t('tools.calculator.position_value_label')} value={fmtVND(result.positionValue)} />
                <Cell label={t('tools.calculator.total_risk_label')} value={fmtVND(result.actualRiskAmount)} accent="#dc2626" />
                <Cell label={t('tools.calculator.actual_risk_pct_label')} value={`${result.actualRiskPct.toFixed(2)}%`} accent="#dc2626" />
                <Cell label={t('tools.calculator.capital_usage_label')} value={`${result.exposurePct.toFixed(1)}%`} />
              </div>

              <div style={{ borderTop: '1px solid #f3f4f6', paddingTop: 12 }}>
                <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <TrendingDown size={12} /> {t('tools.calculator.r_multiple_target_label')}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, fontSize: 13 }}>
                  <Cell label="1R" value={fmtNum(result.r1Target)} accent="#10b981" small />
                  <Cell label="2R" value={fmtNum(result.r2Target)} accent="#10b981" small />
                  <Cell label="3R" value={fmtNum(result.r3Target)} accent="#10b981" small />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const Cell = ({ label, value, accent = '#111827', small = false }) => (
  <div>
    <div style={{ fontSize: 11, color: '#6b7280' }}>{label}</div>
    <div style={{ fontSize: small ? 14 : 16, fontWeight: 600, color: accent }}>{value}</div>
  </div>
);

export default PositionCalculator;
