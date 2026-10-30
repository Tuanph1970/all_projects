import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import indicatorService from '../../../services/indicatorService';
import './IndicatorSelector.css';

// Backlog #105 — A TECHNICAL INDICATOR IS ALWAYS A PAST COVARIATE.
//
// Not a policy choice; a consequence. A future covariate is a series whose
// values over the FORECAST HORIZON are already known at prediction time. SMA,
// EMA, RSI, MACD and Bollinger are deterministic functions of price, so knowing
// them over the horizon means knowing the future prices. Offering 'future' or
// 'both' here asked for something unobtainable.
//
// It was not merely useless, it was a leak. In a backtest the whole history is
// on hand, so a 'future' indicator CAN be supplied and the model learns from
// information that will not exist live — the backtest flatters itself and the
// live path collapses. That is the leakage CLAUDE.md C1 forbids.
//
// The server now REFUSES an indicator marked future/both (plan_covariates in
// prediction-service/app/services/darts_trainer.py). This selector no longer
// offers the choice, so the refusal is unreachable from the UI rather than
// being the operator's first sight of the rule.
const INDICATOR_COVARIATE_TYPE = 'past';

const IndicatorSelector = ({ solutionId, onIndicatorsChange, modelCovariateConfig }) => {
  const { t } = useTranslation();
  // modelCovariateConfig: { hasPastCovariate: boolean, hasFutureCovariate: boolean }
  // Determines which covariate options to show in dropdowns

  // An indicator's covariate type does not depend on the model — see
  // INDICATOR_COVARIATE_TYPE. A future-only model cannot use indicators at all,
  // which is surfaced as a warning rather than by mislabelling them 'future'.
  const getDefaultCovariateType = () => INDICATOR_COVARIATE_TYPE;

  const [indicators, setIndicators] = useState({
    trend: [],
    momentum: [],
    volatility: [],
    volume: []
  });
  const [selectedIndicators, setSelectedIndicators] = useState({
    trend: null,
    momentum: null,
    volatility: null,
    volume: null
  });
  const [parameters, setParameters] = useState({
    trend: {},
    momentum: {},
    volatility: {},
    volume: {}
  });
  // Initialize covariate types based on model config
  const initialCovariateType = getDefaultCovariateType();
  const [covariateTypes, setCovariateTypes] = useState({
    trend: initialCovariateType,
    momentum: initialCovariateType,
    volatility: initialCovariateType,
    volume: initialCovariateType
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadIndicators();
    if (solutionId) {
      loadSolutionIndicators();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [solutionId]);

  const loadIndicators = async () => {
    try {
      setLoading(true);
      const data = await indicatorService.getAllIndicators();
      setIndicators(data);
      setError(null);
    } catch (err) {
      setError('Failed to load indicators: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadSolutionIndicators = async () => {
    try {
      const data = await indicatorService.getSolutionIndicators(solutionId);
      const newSelected = {};
      const newParams = {};
      const newCovariateTypes = {};

      ['trend', 'momentum', 'volatility', 'volume'].forEach(type => {
        if (data[type]) {
          newSelected[type] = data[type].id;
          newParams[type] = data[type].parameters || {};
          newCovariateTypes[type] = data[type].covariate_type || 'past';
        }
      });

      setSelectedIndicators(newSelected);
      setParameters(newParams);
      setCovariateTypes(newCovariateTypes);
    } catch (err) {
      console.error('Failed to load solution indicators:', err);
    }
  };

  const handleIndicatorSelect = (type, indicatorId) => {
    const indicator = indicators[type].find(ind => ind.id === parseInt(indicatorId));

    setSelectedIndicators(prev => ({
      ...prev,
      [type]: indicatorId ? parseInt(indicatorId) : null
    }));

    // Set default parameters
    if (indicator) {
      setParameters(prev => ({
        ...prev,
        [type]: indicator.default_parameters || {}
      }));

      // No model-dependent branch here any more: an indicator is a past
      // covariate whatever the model supports (Backlog #105).
      setCovariateTypes(prev => (
        prev[type] === INDICATOR_COVARIATE_TYPE
          ? prev
          : { ...prev, [type]: INDICATOR_COVARIATE_TYPE }
      ));
    }
  };

  const handleParameterChange = (type, paramName, value) => {
    setParameters(prev => ({
      ...prev,
      [type]: {
        ...prev[type],
        [paramName]: value
      }
    }));
  };

  const handleSave = async (e) => {
    // Prevent event propagation to avoid closing parent modal
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    if (!solutionId) {
      // If no solution ID, pass data to parent component
      if (onIndicatorsChange) {
        onIndicatorsChange({
          trend_indicator: selectedIndicators.trend ? {
            id: selectedIndicators.trend,
            covariate_type: covariateTypes.trend,
            parameters: parameters.trend
          } : null,
          momentum_indicator: selectedIndicators.momentum ? {
            id: selectedIndicators.momentum,
            covariate_type: covariateTypes.momentum,
            parameters: parameters.momentum
          } : null,
          volatility_indicator: selectedIndicators.volatility ? {
            id: selectedIndicators.volatility,
            covariate_type: covariateTypes.volatility,
            parameters: parameters.volatility
          } : null,
          volume_indicator: selectedIndicators.volume ? {
            id: selectedIndicators.volume,
            covariate_type: covariateTypes.volume,
            parameters: parameters.volume
          } : null
        });
      }
      return;
    }

    try {
      setSaving(true);
      const data = {
        trend_indicator: selectedIndicators.trend ? {
          id: selectedIndicators.trend,
          covariate_type: covariateTypes.trend,
          parameters: parameters.trend
        } : null,
        momentum_indicator: selectedIndicators.momentum ? {
          id: selectedIndicators.momentum,
          covariate_type: covariateTypes.momentum,
          parameters: parameters.momentum
        } : null,
        volatility_indicator: selectedIndicators.volatility ? {
          id: selectedIndicators.volatility,
          covariate_type: covariateTypes.volatility,
          parameters: parameters.volatility
        } : null,
        volume_indicator: selectedIndicators.volume ? {
          id: selectedIndicators.volume,
          covariate_type: covariateTypes.volume,
          parameters: parameters.volume
        } : null
      };

      await indicatorService.setSolutionIndicators(solutionId, data);

      if (onIndicatorsChange) {
        onIndicatorsChange(data);
      }

      setError(null);
      alert(t('indicator_selector.save_success'));
    } catch (err) {
      setError('Failed to save indicators: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const getCategoryIcon = (category) => {
    const icons = {
      trend: '📈',
      momentum: '⚡',
      volatility: '📊',
      volume: '📦'
    };
    return icons[category];
  };

  // Backlog #105 — repairs legacy rows. Solutions saved before this change may
  // carry covariate_type 'future' or 'both' in solution_indicators; the server
  // would refuse those at training time. Coerce them on load so the operator
  // sees the correct value instead of a training failure later.
  useEffect(() => {
    setCovariateTypes(prev => {
      const stale = ['trend', 'momentum', 'volatility', 'volume']
        .filter(type => prev[type] !== INDICATOR_COVARIATE_TYPE);
      if (stale.length === 0) return prev;
      const updated = { ...prev };
      stale.forEach(type => { updated[type] = INDICATOR_COVARIATE_TYPE; });
      return updated;
    });
  }, [indicators]);

  const getSelectedIndicator = (type) => {
    if (!selectedIndicators[type]) return null;
    return indicators[type]?.find(ind => ind.id === selectedIndicators[type]);
  };

  if (loading) {
    return <div className="indicator-selector-loading">{t('indicator_selector.loading')}</div>;
  }

  return (
    <div className="indicator-selector">
      <h3 className="selector-title">{t('indicator_selector.title')}</h3>
      <p className="selector-subtitle">
        {t('indicator_selector.subtitle')}
      </p>

      {error && <div className="selector-error">{error}</div>}

      <div className="indicator-categories">
        {['trend', 'momentum', 'volatility', 'volume'].map((type) => {
          const selectedInd = getSelectedIndicator(type);

          return (
            <div key={type} className="indicator-category">
              <div className="category-header">
                <span className="category-icon">{getCategoryIcon(type)}</span>
                <h4>{type.charAt(0).toUpperCase() + type.slice(1)} {t('indicator_selector.indicator_label')}</h4>
                {selectedIndicators[type] && <span className="required-badge">{t('indicator_selector.selected_badge')}</span>}
              </div>

              <select
                className="indicator-select"
                value={selectedIndicators[type] || ''}
                onChange={(e) => handleIndicatorSelect(type, e.target.value)}
              >
                <option value="">{t('indicator_selector.select_placeholder', { type })}</option>
                {indicators[type]?.map((indicator) => (
                  <option key={indicator.id} value={indicator.id}>
                    {indicator.name} - {indicator.description}
                  </option>
                ))}
              </select>

              {selectedIndicators[type] && (
                <div className="covariate-type-selector">
                  <label>{t('indicator_selector.covariate_type')}</label>
                  {/* Backlog #104/#105 — a FIXED value, not a dropdown. A
                      one-option select reads as a choice the operator has yet
                      to make; this states the rule and says why. */}
                  <span className="covariate-type-fixed">
                    &#128202; {t('indicator_selector.past_label')}
                  </span>
                  <span className="covariate-help-text">
                    {t('indicator_selector.indicator_always_past_help')}
                  </span>
                  {modelCovariateConfig && !Boolean(modelCovariateConfig.hasPastCovariate) && (
                    <span className="covariate-blocked" role="alert">
                      &#9888; {t('indicator_selector.model_rejects_indicators')}
                    </span>
                  )}
                </div>
              )}

              {selectedInd && selectedInd.default_parameters && Object.keys(selectedInd.default_parameters).length > 0 && (
                <div className="parameter-inputs">
                  <h5>{t('indicator_selector.parameters_title')}</h5>
                  {Object.entries(selectedInd.default_parameters).map(([paramName, defaultValue]) => (
                    <div key={paramName} className="parameter-input">
                      <label>{paramName}:</label>
                      <input
                        type="number"
                        value={parameters[type][paramName] || defaultValue}
                        onChange={(e) => handleParameterChange(type, paramName, parseFloat(e.target.value))}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Backlog #104 — name the genuine future-covariate source, so "this
          model supports future covariates" does not read as an invitation to
          mark an indicator 'future'. The DARTS engine adds these automatically
          (plan_covariates) and they are not operator-selectable, which is why
          this is a statement rather than an empty picker. The note NAMES the
          Darts engine deliberately, and that qualifier survived #109's flip of
          the default (2026-10-30, DEFAULT_TRAINING_ENGINE in
          prediction-service solution_routes.py). It now reads as true of the
          default path rather than as a warning about it — but it must stay
          qualified, because the older tabular engine is still reachable via
          engine='tabular' and builds no calendar features at all, so an
          unqualified "supplied automatically" would be false there. */}
      {modelCovariateConfig && Boolean(modelCovariateConfig.hasFutureCovariate) && (
        <p className="covariate-calendar-note">
          &#128197; {t('indicator_selector.calendar_future_note')}
        </p>
      )}

      <div className="selector-actions">
        <button
          type="button"
          className="save-button"
          onClick={handleSave}
          disabled={saving || !selectedIndicators.trend || !selectedIndicators.momentum ||
                    !selectedIndicators.volatility || !selectedIndicators.volume}
        >
          {saving ? t('indicator_selector.saving_btn') : solutionId ? t('indicator_selector.save_btn') : t('indicator_selector.set_btn')}
        </button>
        {(!selectedIndicators.trend || !selectedIndicators.momentum ||
          !selectedIndicators.volatility || !selectedIndicators.volume) && (
          <p className="validation-message">
            {t('indicator_selector.validation_msg')}
          </p>
        )}
      </div>
    </div>
  );
};

export default IndicatorSelector;
