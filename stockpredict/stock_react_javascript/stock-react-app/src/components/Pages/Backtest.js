import React, { useState } from 'react';
import { Activity, AlertTriangle, History, Play, Target } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import modelService from '../../services/modelService';

const MODEL_TYPES = [
  { value: 'xgboost', label: 'XGBoost' },
  { value: 'lightgbm', label: 'LightGBM' },
  { value: 'random_forest', label: 'Random Forest' },
  { value: 'linear_regression', label: 'Linear Regression' },
  { value: 'arima', label: 'ARIMA' },
  { value: 'lstm', label: 'LSTM' },
];

const todayISO = () => new Date().toISOString().slice(0, 10);
const daysAgoISO = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
};

const fmtPct = (v) => `${(Number(v) * 100).toFixed(2)}%`;
const fmtNum = (v, digits = 4) => Number(v).toFixed(digits);

const Backtest = () => {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    symbol: 'FPT',
    model_type: 'xgboost',
    start_date: daysAgoISO(180),
    end_date: todayISO(),
    prediction_horizon: 5,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const onChange = (field) => (e) => {
    const value = field === 'prediction_horizon' ? Number(e.target.value) : e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (!form.symbol.trim()) {
      setError(t('backtest.error_symbol_required'));
      return;
    }
    if (new Date(form.start_date) >= new Date(form.end_date)) {
      setError(t('backtest.error_date_range'));
      return;
    }

    setLoading(true);
    const response = await modelService.runBacktest({
      ...form,
      symbol: form.symbol.trim().toUpperCase(),
    });
    setLoading(false);

    if (response.success) {
      setResult(response.data);
    } else {
      setError(response.error || t('backtest.error_run_failed'));
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <h1 style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <History color="#8b5cf6" />
        {t('backtest.title')}
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24 }}>
        {t('backtest.description')}
      </p>

      <div className="responsive-stack" style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: 24 }}>
        {/* Form */}
        <form
          onSubmit={onSubmit}
          style={{
            background: '#fff',
            padding: 20,
            borderRadius: 8,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
        >
          <h3 style={{ marginTop: 0, marginBottom: 16 }}>{t('backtest.parameters_header')}</h3>

          <div style={{ marginBottom: 12 }}>
            <label htmlFor="bt-symbol" style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              {t('backtest.symbol_label')}
            </label>
            <input
              id="bt-symbol"
              type="text"
              value={form.symbol}
              onChange={onChange('symbol')}
              style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 4 }}
              maxLength={20}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label htmlFor="bt-model" style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              {t('backtest.model_type_label')}
            </label>
            <select
              id="bt-model"
              value={form.model_type}
              onChange={onChange('model_type')}
              style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 4 }}
            >
              {MODEL_TYPES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div className="responsive-stack" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div>
              <label htmlFor="bt-start" style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                {t('backtest.from_date')}
              </label>
              <input
                id="bt-start"
                type="date"
                value={form.start_date}
                onChange={onChange('start_date')}
                style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 4 }}
              />
            </div>
            <div>
              <label htmlFor="bt-end" style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
                {t('backtest.to_date')}
              </label>
              <input
                id="bt-end"
                type="date"
                value={form.end_date}
                onChange={onChange('end_date')}
                style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 4 }}
              />
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label htmlFor="bt-horizon" style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
              {t('backtest.prediction_horizon')}
            </label>
            <input
              id="bt-horizon"
              type="number"
              min={1}
              max={30}
              value={form.prediction_horizon}
              onChange={onChange('prediction_horizon')}
              style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 4 }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '10px 16px',
              background: loading ? '#a78bfa' : '#8b5cf6',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
            }}
          >
            <Play size={16} />
            {loading ? t('backtest.running') : t('backtest.run')}
          </button>

          {error && (
            <div
              role="alert"
              style={{
                marginTop: 12,
                padding: 10,
                background: '#fee2e2',
                color: '#991b1b',
                borderRadius: 4,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <AlertTriangle size={16} />
              <span>{error}</span>
            </div>
          )}
        </form>

        {/* Results */}
        <div
          style={{
            background: '#fff',
            padding: 20,
            borderRadius: 8,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            minHeight: 320,
          }}
        >
          <h3 style={{ marginTop: 0, marginBottom: 16 }}>{t('backtest.results_header')}</h3>

          {!result && !loading && (
            <p style={{ color: '#9ca3af' }}>
              {t('backtest.empty_message')}
            </p>
          )}

          {loading && (
            <p style={{ color: '#6b7280' }} aria-live="polite">
              {t('backtest.analyzing')}
            </p>
          )}

          {result && (
            <div data-testid="bt-results">
              <div style={{ marginBottom: 16, color: '#6b7280', fontSize: 14 }}>
                <strong style={{ color: '#111827' }}>{result.symbol}</strong>
                {' · '}
                {result.model_type}
                {' · '}
                {result.period}
              </div>

              {/* Direction accuracy bar */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <Target size={16} color="#8b5cf6" />
                  <span style={{ fontWeight: 500 }}>{t('backtest.direction_accuracy')}</span>
                  <span data-testid="bt-direction-accuracy" style={{ marginLeft: 'auto', fontWeight: 600 }}>
                    {fmtPct(result.direction_accuracy)}
                  </span>
                </div>
                <div style={{ background: '#e5e7eb', borderRadius: 4, height: 10, overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${Math.min(100, Math.max(0, result.direction_accuracy * 100))}%`,
                      background: result.direction_accuracy >= 0.5 ? '#22c55e' : '#ef4444',
                      height: '100%',
                    }}
                  />
                </div>
                <div style={{ marginTop: 4, fontSize: 12, color: '#6b7280' }}>
                  {result.correct_direction} / {result.total_predictions} {t('backtest.predictions_unit')}
                </div>
              </div>

              <div className="responsive-stack" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Metric label="MAE" value={fmtNum(result.mean_absolute_error)} />
                <Metric label="RMSE" value={fmtNum(result.root_mean_squared_error)} />
                <Metric
                  label={t('backtest.average_confidence')}
                  value={fmtPct(result.average_confidence)}
                  icon={<Activity size={14} color="#6366f1" />}
                />
                <Metric label={t('backtest.total_predictions')} value={result.total_predictions} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const Metric = ({ label, value, icon }) => (
  <div style={{ padding: 12, background: '#f9fafb', borderRadius: 6 }}>
    <div style={{ fontSize: 12, color: '#6b7280', display: 'flex', alignItems: 'center', gap: 6 }}>
      {icon}
      {label}
    </div>
    <div style={{ fontSize: 18, fontWeight: 600, color: '#111827', marginTop: 4 }}>{value}</div>
  </div>
);

export default Backtest;
