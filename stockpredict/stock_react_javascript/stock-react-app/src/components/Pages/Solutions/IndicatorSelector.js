import React, { useState, useEffect } from 'react';
import indicatorService from '../../../services/indicatorService';
import './IndicatorSelector.css';

const IndicatorSelector = ({ solutionId, onIndicatorsChange, modelCovariateConfig }) => {
  // modelCovariateConfig: { hasPastCovariate: boolean, hasFutureCovariate: boolean }
  // Determines which covariate options to show in dropdowns

  // Helper function to get default covariate type based on model config
  const getDefaultCovariateType = (config) => {
    // Use Boolean() to properly convert values (handles 0/1, true/false, undefined)
    const hasPast = Boolean(config?.hasPastCovariate);
    const hasFuture = Boolean(config?.hasFutureCovariate);

    console.log('getDefaultCovariateType:', { config, hasPast, hasFuture });

    if (hasPast && hasFuture) {
      return 'past'; // default to past when both available
    } else if (hasPast) {
      return 'past';
    } else if (hasFuture) {
      return 'future';
    }
    return 'past'; // fallback when no model selected
  };

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
  const initialCovariateType = getDefaultCovariateType(modelCovariateConfig);
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

      // Also ensure covariate type is valid for current model
      const hasPast = Boolean(modelCovariateConfig?.hasPastCovariate);
      const hasFuture = Boolean(modelCovariateConfig?.hasFutureCovariate);

      let validValues = [];
      if (hasPast && hasFuture) {
        validValues = ['past', 'future', 'both'];
      } else if (hasPast) {
        validValues = ['past'];
      } else if (hasFuture) {
        validValues = ['future'];
      } else {
        // If model config not set, default based on what's available
        validValues = hasFuture ? ['future'] : ['past'];
      }

      setCovariateTypes(prev => {
        if (!validValues.includes(prev[type])) {
          return { ...prev, [type]: validValues[0] };
        }
        return prev;
      });
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

  const handleCovariateTypeChange = (type, covariateType) => {
    setCovariateTypes(prev => ({
      ...prev,
      [type]: covariateType
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
      alert('Indicators saved successfully!');
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

  // Get available covariate options based on model configuration
  const getAvailableCovariateOptions = () => {
    const options = [];
    // Use Boolean() to properly convert values (handles 0/1, true/false, undefined)
    const hasPast = Boolean(modelCovariateConfig?.hasPastCovariate);
    const hasFuture = Boolean(modelCovariateConfig?.hasFutureCovariate);

    // Debug logging to help diagnose issues
    console.log('getAvailableCovariateOptions:', {
      modelCovariateConfig,
      hasPast,
      hasFuture,
      rawPast: modelCovariateConfig?.hasPastCovariate,
      rawFuture: modelCovariateConfig?.hasFutureCovariate
    });

    if (hasPast && hasFuture) {
      // Model supports both - show all 3 options
      options.push({ value: 'past', label: 'Past (Historical)', icon: '📊', help: 'Technical indicators use historical data' });
      options.push({ value: 'future', label: 'Future (Scheduled Events)', icon: '📅', help: 'For known future events (earnings, calendar)' });
      options.push({ value: 'both', label: 'Both (Dual)', icon: '🔄', help: 'Available in both historical and future' });
    } else if (hasPast) {
      // Only past covariate supported
      options.push({ value: 'past', label: 'Past (Historical)', icon: '📊', help: 'Technical indicators use historical data' });
    } else if (hasFuture) {
      // Only future covariate supported
      options.push({ value: 'future', label: 'Future (Scheduled Events)', icon: '📅', help: 'For known future events (earnings, calendar)' });
    } else {
      // No covariate config or model not selected - show both options with warning
      console.warn('No valid covariate config - model may not be selected');
      options.push({ value: 'past', label: 'Past (Historical)', icon: '📊', help: 'Technical indicators use historical data' });
      options.push({ value: 'future', label: 'Future (Scheduled Events)', icon: '📅', help: 'For known future events (earnings, calendar)' });
    }

    return options;
  };

  // Auto-adjust covariate types when model config changes
  useEffect(() => {
    // Use Boolean() to properly convert values (handles 0/1, true/false, undefined)
    const hasPast = Boolean(modelCovariateConfig?.hasPastCovariate);
    const hasFuture = Boolean(modelCovariateConfig?.hasFutureCovariate);

    console.log('useEffect - modelCovariateConfig changed:', {
      modelCovariateConfig,
      hasPast,
      hasFuture
    });

    let validValues = [];
    if (hasPast && hasFuture) {
      validValues = ['past', 'future', 'both'];
    } else if (hasPast) {
      validValues = ['past'];
    } else if (hasFuture) {
      validValues = ['future'];
    } else {
      // No model selected or no covariate support - allow both
      validValues = ['past', 'future'];
    }

    const defaultValue = validValues[0];

    // Update covariate types to valid values if current selection is not valid
    setCovariateTypes(prev => {
      const updated = { ...prev };
      let hasChanges = false;
      ['trend', 'momentum', 'volatility', 'volume'].forEach(type => {
        if (!validValues.includes(prev[type])) {
          // Default to first available option
          updated[type] = defaultValue;
          hasChanges = true;
          console.log(`Updating covariate type for ${type}: ${prev[type]} -> ${defaultValue}`);
        }
      });
      // Only return new object if there are changes to avoid infinite loop
      return hasChanges ? updated : prev;
    });
  }, [modelCovariateConfig?.hasPastCovariate, modelCovariateConfig?.hasFutureCovariate]);

  const getSelectedIndicator = (type) => {
    if (!selectedIndicators[type]) return null;
    return indicators[type]?.find(ind => ind.id === selectedIndicators[type]);
  };

  if (loading) {
    return <div className="indicator-selector-loading">Loading indicators...</div>;
  }

  return (
    <div className="indicator-selector">
      <h3 className="selector-title">Select Technical Indicators</h3>
      <p className="selector-subtitle">
        Choose one indicator from each category to use as features for prediction
      </p>

      {error && <div className="selector-error">{error}</div>}

      <div className="indicator-categories">
        {['trend', 'momentum', 'volatility', 'volume'].map((type) => {
          const selectedInd = getSelectedIndicator(type);

          return (
            <div key={type} className="indicator-category">
              <div className="category-header">
                <span className="category-icon">{getCategoryIcon(type)}</span>
                <h4>{type.charAt(0).toUpperCase() + type.slice(1)} Indicator</h4>
                {selectedIndicators[type] && <span className="required-badge">✓ Selected</span>}
              </div>

              <select
                className="indicator-select"
                value={selectedIndicators[type] || ''}
                onChange={(e) => handleIndicatorSelect(type, e.target.value)}
              >
                <option value="">-- Select {type} indicator --</option>
                {indicators[type]?.map((indicator) => (
                  <option key={indicator.id} value={indicator.id}>
                    {indicator.name} - {indicator.description}
                  </option>
                ))}
              </select>

              {selectedIndicators[type] && (
                <div className="covariate-type-selector">
                  <label>Covariate Type:</label>
                  {(() => {
                    const availableOptions = getAvailableCovariateOptions();
                    const currentOption = availableOptions.find(opt => opt.value === covariateTypes[type]) || availableOptions[0];

                    return (
                      <>
                        <select
                          className="covariate-type-select"
                          value={covariateTypes[type] || availableOptions[0]?.value || 'past'}
                          onChange={(e) => handleCovariateTypeChange(type, e.target.value)}
                          title={availableOptions.map(opt => `${opt.label}: ${opt.help}`).join(' | ')}
                          disabled={availableOptions.length === 1}
                        >
                          {availableOptions.map(option => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        <span className="covariate-help-text">
                          {currentOption?.icon} {currentOption?.help}
                        </span>
                        {availableOptions.length === 1 && (
                          <span className="covariate-model-info">
                            ℹ️ Model only supports {availableOptions[0]?.label.toLowerCase()}
                          </span>
                        )}
                      </>
                    );
                  })()}
                </div>
              )}

              {selectedInd && selectedInd.default_parameters && Object.keys(selectedInd.default_parameters).length > 0 && (
                <div className="parameter-inputs">
                  <h5>Parameters:</h5>
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

      <div className="selector-actions">
        <button
          type="button"
          className="save-button"
          onClick={handleSave}
          disabled={saving || !selectedIndicators.trend || !selectedIndicators.momentum ||
                    !selectedIndicators.volatility || !selectedIndicators.volume}
        >
          {saving ? 'Saving...' : solutionId ? 'Save Indicators' : 'Set Indicators'}
        </button>
        {(!selectedIndicators.trend || !selectedIndicators.momentum ||
          !selectedIndicators.volatility || !selectedIndicators.volume) && (
          <p className="validation-message">
            ⚠️ Please select one indicator from each category
          </p>
        )}
      </div>
    </div>
  );
};

export default IndicatorSelector;
